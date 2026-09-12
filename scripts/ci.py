#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

PACKAGING_GIT = "https://github.com/amozeo/nixos-cosmic.git"
SOURCE_BRANCH = "source"
SOURCE_REPO = os.environ.get("GITHUB_REPOSITORY", "jmspwr/cosmic-cache")
CLIENT_FILES = [
    ".github/workflows/cache.yml",
    "cache.json",
    "default.nix",
    "packages.nix",
    "retention-root.nix",
    "scripts/ci.py",
]


def run(*args: str, capture: bool = True, cwd: str | Path | None = None,
        env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args,
        check=True,
        text=True,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def dump(path: str | Path, value: object) -> None:
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def cache() -> dict:
    value = json.loads(Path("cache.json").read_text())
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", value["name"]):
        raise ValueError("Invalid cache name")
    if value["uri"].rstrip("/") != f'https://{value["name"]}.cachix.org':
        raise ValueError("Unexpected Cachix URL")
    keys = value.get("publicSigningKeys", [])
    if not keys or not all(
        isinstance(k, str) and k.startswith(value["name"] + ".cachix.org-")
        for k in keys
    ):
        raise ValueError("Missing/invalid cache public signing keys")
    return value


def options() -> list[str]:
    c = cache()
    return [
        "--option", "extra-substituters", c["uri"],
        "--option", "extra-trusted-public-keys", " ".join(c["publicSigningKeys"]),
        "--option", "narinfo-cache-negative-ttl", "0",
        "--option", "fallback", "false",
    ]


def snapshot(revision: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid source revision")
    dump("snapshot.json", {"schema": 2, "url": f"github:{SOURCE_REPO}/{revision}"})


def selected_package(name: str) -> bool:
    return (
        (
            name.startswith("cosmic-")
            and not name.startswith("cosmic-ext-")
            or name in {"pop-launcher", "xdg-desktop-portal-cosmic", "cutecosmic"}
        )
        and name != "cosmic-applibrary"
    )


def component_sources(root: str | Path) -> dict[str, dict[str, str]]:
    root = Path(root)
    sources: dict[str, dict[str, str]] = {}
    required = {
        "cosmic-comp", "cosmic-greeter", "cosmic-panel",
        "cosmic-session", "cosmic-settings", "xdg-desktop-portal-cosmic",
    }
    seen_required: set[str] = set()

    for package_dir in sorted((root / "pkgs").iterdir()):
        if not package_dir.is_dir() or not selected_package(package_dir.name):
            continue
        package_file = package_dir / "package.nix"
        if not package_file.is_file():
            continue
        text = package_file.read_text()
        block = re.search(r"\bsrc\s*=\s*fetchFromGitHub\s*\{(.*?)\n\s*\};", text, re.S)
        if block is None:
            continue
        body = block.group(1)
        owner = re.search(r'\bowner\s*=\s*"([^"]+)"\s*;', body)
        repo = re.search(r'\brepo\s*=\s*"([^"]+)"\s*;', body)
        rev = re.search(r'\brev\s*=\s*"([0-9a-f]{40})"\s*;', body)
        if not (owner and repo and rev):
            raise RuntimeError(f"Cannot track primary GitHub source for {package_dir.name}")
        upstream = f"{owner.group(1)}/{repo.group(1)}"
        value = {"package": package_dir.name, "rev": rev.group(1)}
        existing = sources.get(upstream)
        if existing and existing["rev"] != value["rev"]:
            raise RuntimeError(f"Conflicting pinned revisions for {upstream}")
        sources[upstream] = value
        if package_dir.name in required:
            seen_required.add(package_dir.name)

    missing = sorted(required - seen_required)
    if missing:
        raise RuntimeError("Missing tracked core COSMIC sources: " + ", ".join(missing))
    return sources


def remote_head(repo: str) -> tuple[str, str]:
    output = run("git", "ls-remote", "--exit-code", f"https://github.com/{repo}.git", "HEAD")
    sha = output.split()[0] if output else ""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError(f"Cannot resolve HEAD for {repo}")
    return repo, sha


def remote_heads(repos: list[str]) -> dict[str, str]:
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(repos)))) as pool:
        return dict(pool.map(remote_head, repos))


def public_branch_head(branch: str) -> str:
    output = run(
        "git", "ls-remote", "--heads",
        f"https://github.com/{SOURCE_REPO}.git", f"refs/heads/{branch}",
    )
    if not output:
        return ""
    sha = output.split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError(f"Invalid {branch} branch revision")
    return sha


def source_metadata(revision: str) -> dict | None:
    if not revision:
        return None
    url = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{revision}/.cosmic-cache-source.json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def client_digest() -> str:
    digest = hashlib.sha256()
    for path in CLIENT_FILES:
        digest.update(path.encode() + b"\0" + Path(path).read_bytes() + b"\0")
    return digest.hexdigest()


def published() -> dict:
    url = f"https://raw.githubusercontent.com/{SOURCE_REPO}/cached/cache-proof.json"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {}
        raise


def github_push_env(token: str) -> dict[str, str]:
    env = os.environ.copy()
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {auth}"
    return env


def refresh_source() -> tuple[str, bool]:
    previous = public_branch_head(SOURCE_BRANCH)
    previous_meta = source_metadata(previous)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to publish source snapshots")

    with tempfile.TemporaryDirectory(prefix="cosmic-source-") as tmp:
        run(
            "git", "clone", "--filter=blob:none", "--no-tags", "--branch", "main",
            PACKAGING_GIT, tmp, capture=False,
        )
        base = run("git", "rev-parse", "HEAD", cwd=tmp)
        pinned = component_sources(tmp)
        heads = remote_heads(sorted(pinned))

        if (
            previous_meta is not None
            and previous_meta.get("schema") == 1
            and previous_meta.get("packagingBase") == base
            and previous_meta.get("components") == heads
        ):
            print(f"COSMIC source snapshot already current at {previous}")
            return previous, False

        run("git", "config", "user.name", "github-actions[bot]", cwd=tmp)
        run(
            "git", "config", "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com", cwd=tmp,
        )
        update_path = run(
            "nix", "build", ".#update", "--no-link", "--print-out-paths",
            cwd=tmp, env=os.environ.copy(),
        ).splitlines()[-1]
        run(
            f"{update_path}/bin/cosmic-unstable-update",
            capture=False, cwd=tmp, env=os.environ.copy(),
        )

        pinned_after = component_sources(tmp)
        heads_after = remote_heads(sorted(pinned_after))
        stale = {
            repo: {
                "package": data["package"],
                "pinned": data["rev"],
                "head": heads_after[repo],
            }
            for repo, data in pinned_after.items()
            if data["rev"] != heads_after[repo]
        }
        if stale:
            raise RuntimeError(
                "Updater did not reach current component HEADs: "
                + json.dumps(stale, sort_keys=True)
            )

        dump(
            Path(tmp) / ".cosmic-cache-source.json",
            {
                "schema": 1,
                "packagingBase": base,
                "components": heads_after,
                "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        )
        run("git", "add", "-A", cwd=tmp)
        # Source snapshots carry packaging data, never upstream CI workflow files.
        run(
            "git", "rm", "-r", "--cached", "--ignore-unmatch", ".github",
            cwd=tmp, capture=False,
        )
        if run("git", "ls-files", ".github", cwd=tmp):
            raise RuntimeError("Source snapshot unexpectedly contains .github files")
        tree = run("git", "write-tree", cwd=tmp)

        parent_args: list[str] = []
        if previous:
            run(
                "git", "fetch", "--no-tags", f"https://github.com/{SOURCE_REPO}.git",
                f"refs/heads/{SOURCE_BRANCH}", cwd=tmp, capture=False,
            )
            fetched = run("git", "rev-parse", "FETCH_HEAD", cwd=tmp)
            if fetched != previous:
                raise RuntimeError("Source branch changed during refresh; retry safely")
            parent_args = ["-p", previous]

        revision = run(
            "git", "commit-tree", tree, *parent_args,
            "-m", "Refresh COSMIC component HEADs", cwd=tmp,
        )
        run(
            "git", "push", f"https://github.com/{SOURCE_REPO}.git",
            f"{revision}:refs/heads/{SOURCE_BRANCH}", cwd=tmp,
            env=github_push_env(token), capture=False,
        )
        print(f"Published source snapshot {revision} from packaging base {base}")
        return revision, True


def package_info() -> dict:
    return json.loads(
        run(
            "nix", "eval", "--impure", "--json", "--file", "packages.nix", "--apply",
            'builtins.mapAttrs (name: p: { path = toString p.out; version = p.version or "unknown"; preferLocalBuild = p.preferLocalBuild or false; })',
        )
    )


def resolve() -> None:
    cache()
    revision, source_changed = refresh_source()
    snapshot(revision)
    names = sorted(package_info())
    required = {
        "cosmic-comp", "cosmic-session", "cosmic-greeter",
        "cosmic-panel", "cosmic-settings", "xdg-desktop-portal-cosmic",
    }
    if not required <= set(names):
        raise RuntimeError("Source snapshot is missing required COSMIC packages")
    if not names or len(names) > 100:
        raise RuntimeError("Unexpected package matrix size")

    proof = published()
    build_needed = (
        proof.get("revision") != revision
        or proof.get("clientDigest") != client_digest()
    )
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write("revision=" + revision + "\n")
        out.write("matrix=" + json.dumps(names, separators=(",", ":")) + "\n")
        out.write("build=" + ("true" if build_needed else "false") + "\n")
    print(
        f"Resolved {len(names)} package outputs at {revision}; "
        f"source_changed={str(source_changed).lower()} "
        f"build={str(build_needed).lower()}"
    )


def build(name: str, revision: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Invalid package name")
    snapshot(revision)
    root = run(
        "nix-build", "packages.nix", "-A", name + ".out", "--no-out-link",
        "--cores", "2", "--max-jobs", "1", *options(),
    )
    if not re.fullmatch(r"/nix/store/[0-9a-z]{32}-[^\s]+", root):
        raise RuntimeError("Expected exactly one store output")
    Path("built-output.txt").write_text(root + "\n")
    print(root)


def push() -> None:
    root = Path("built-output.txt").read_text().strip()
    if not os.environ.get("CACHIX_AUTH_TOKEN"):
        raise RuntimeError("CACHIX_AUTH_TOKEN is not configured")
    run(
        "nix", "run", "nixpkgs#cachix", "--", "push",
        cache()["name"], root, capture=False,
    )


def verify(revision: str) -> None:
    snapshot(revision)
    info = package_info()
    if any(
        p["preferLocalBuild"] not in (False, "", "0", None)
        for p in info.values()
    ):
        raise RuntimeError("A source package forces local builds; refuse publication")

    expression = "builtins.map (p: p.out) (builtins.attrValues (import ./packages.nix))"
    run(
        "nix-build", "--expr", expression, "--no-out-link", "--max-jobs", "0",
        "--option", "builders", "", *options(), capture=False,
    )

    expression = (
        'let '
        's = builtins.fromJSON (builtins.readFile ./snapshot.json); '
        'u = builtins.getFlake s.url; '
        'n = u.inputs.nixpkgs.lib.nixosSystem { '
        'system = "x86_64-linux"; '
        'modules = [ ./default.nix ({ ... }: { '
        'boot.isContainer = true; '
        'services.desktopManager.cosmic.enable = true; '
        'services.displayManager.cosmic-greeter.enable = true; '
        'system.stateVersion = "25.11"; '
        '}) ]; '
        '}; '
        'p = import ./packages.nix; '
        'in builtins.all (name: n.pkgs.${name}.outPath == p.${name}.outPath) '
        '(builtins.attrNames p)'
    )
    if run("nix", "eval", "--impure", "--json", "--expr", expression) != "true":
        raise RuntimeError("NixOS integration changed the cached package outputs")

    dump(
        "cache-proof.json",
        {
            "schema": 2,
            "verifiedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "revision": revision,
            "clientDigest": client_digest(),
            "builderRevision": os.environ["GITHUB_SHA"],
            "method": (
                "fresh-job nix-build: max-jobs=0, no remote builders; "
                "exact module-output equality"
            ),
            "packages": info,
        },
    )
    print("Cached package outputs and module-output identity verified")


def retain() -> None:
    root = run("nix-build", "retention-root.nix", "--no-out-link", *options())
    c = cache()["name"]
    run("nix", "run", "nixpkgs#cachix", "--", "push", c, root, capture=False)
    run(
        "nix", "run", "nixpkgs#cachix", "--", "pin", c,
        "cosmic-x86_64-linux", root, "--keep-revisions", "2", capture=False,
    )


def publish() -> None:
    for path in ("snapshot.json", "cache-proof.json"):
        if not Path(path).is_file():
            raise RuntimeError(f"Missing publication evidence: {path}")
    remote = run("git", "ls-remote", "--heads", "origin", "refs/heads/cached")
    parent = run("git", "rev-parse", "HEAD")
    if remote:
        run("git", "fetch", "--no-tags", "origin", "refs/heads/cached", capture=False)
        parent = run("git", "rev-parse", "FETCH_HEAD")
    run("git", "config", "user.name", "github-actions[bot]")
    run(
        "git", "config", "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    run("git", "add", "snapshot.json", "cache-proof.json")
    tree = run("git", "write-tree")
    sha = run(
        "git", "commit-tree", tree, "-p", parent,
        "-m", "Publish verified COSMIC cache snapshot",
    )
    run("git", "push", "origin", sha + ":refs/heads/cached", capture=False)
    print("Published cached branch: " + sha)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["resolve", "build", "push", "verify", "retain", "publish"],
    )
    parser.add_argument("--revision", default=os.environ.get("SOURCE_REV", ""))
    parser.add_argument("--package", default=os.environ.get("PACKAGE", ""))
    args = parser.parse_args()
    {
        "resolve": resolve,
        "build": lambda: build(args.package, args.revision),
        "push": push,
        "verify": lambda: verify(args.revision),
        "retain": retain,
        "publish": publish,
    }[args.command]()


if __name__ == "__main__":
    try:
        main()
    except (
        subprocess.CalledProcessError,
        ValueError,
        RuntimeError,
        KeyError,
        OSError,
        urllib.error.URLError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
