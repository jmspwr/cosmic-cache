#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from scripts import cache as shared
from scripts.cache import cache, dump, options, run

PACKAGING_GIT = "https://github.com/amozeo/nixos-cosmic.git"
SOURCE_BRANCH = "source"
SOURCE_REPO = os.environ.get("GITHUB_REPOSITORY", "jmspwr/cosmic-cache")
CLIENT_FILES = [
    ".github/workflows/check.yml",
    ".github/workflows/cosmic.yml",
    "cache.json",
    "cosmic/ci.py",
    "cosmic/default.nix",
    "cosmic/packages.nix",
    "cosmic/retention-root.nix",
    "default.nix",
    "packages.nix",
    "scripts/cache.py",
    "scripts/storage.py",
    "cosmic/check.nix",
    "cosmic/profile.nix",
]


def client_digest() -> str:
    return shared.client_digest(CLIENT_FILES)


def published() -> dict:
    return shared.published("cosmic-cache", "cosmic")


def publish() -> None:
    proof = json.loads(Path("cache-proof.json").read_text())
    validate_proof(proof, evaluate=False)
    if not proof.get("storage") or not proof.get("retentionRoot"):
        raise RuntimeError("Missing successful retention/storage evidence")
    current = {k: v for k, v in published().items() if k not in {"snapshot", "publicationRevision"}}
    if current != proof:
        shared.publish("cosmic-cache", env=github_push_env(os.environ["GITHUB_TOKEN"]),
                       expected_parent=proof["publicationParent"])
    # Keep both snapshots until the advertised branch has advanced successfully.
    pin_root(proof["retentionRoot"])


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
            raise RuntimeError(f"Missing package recipe for {package_dir.name}")
        text = package_file.read_text()
        block = re.search(r"\bsrc\s*=\s*fetchFromGitHub\s*\{(.*?)\n\s*\};", text, re.S)
        if block is None:
            raise RuntimeError(f"Cannot track primary GitHub source for {package_dir.name}")
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


def build_env() -> dict[str, str]:
    # The updater is upstream executable code; it does not need publication secrets.
    return {k: v for k, v in os.environ.items()
            if k not in {"GITHUB_TOKEN", "GH_TOKEN", "CACHIX_AUTH_TOKEN"}
            and not k.startswith(("GIT_CONFIG_", "ACTIONS_RUNTIME_", "ACTIONS_ID_TOKEN_"))}


def github_push_env(token: str) -> dict[str, str]:
    env = build_env()
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {auth}"
    return env


def refresh_source() -> tuple[str, bool]:
    previous = public_branch_head(SOURCE_BRANCH)
    previous_meta = source_metadata(previous)

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
            cwd=tmp, env=build_env(),
        ).splitlines()[-1]
        run(
            f"{update_path}/bin/cosmic-unstable-update",
            capture=False, cwd=tmp, env=build_env(),
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
        run("git", "update-ref", "refs/heads/snapshot", revision, cwd=tmp)
        run("git", "bundle", "create", str(shared.ROOT / "source.bundle"),
            "refs/heads/snapshot", cwd=tmp)
        print(f"Prepared source snapshot {revision} from packaging base {base}")
        return revision, True


def update_source() -> None:
    revision, changed = refresh_source()
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"revision={revision}\nchanged={str(changed).lower()}\n")


def publish_source(revision: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid source revision")
    with tempfile.TemporaryDirectory(prefix="cosmic-publish-") as tmp:
        run("git", "init", tmp)
        run("git", "fetch", str(shared.ROOT / "source.bundle"), "refs/heads/snapshot", cwd=tmp)
        if run("git", "rev-parse", "FETCH_HEAD", cwd=tmp) != revision:
            raise RuntimeError("Source bundle does not match the resolved revision")
        files = run("git", "ls-tree", "--name-only", revision, cwd=tmp).splitlines()
        if ".github" in files or ".cosmic-cache-source.json" not in files:
            raise RuntimeError("Invalid source snapshot contents")
        run("git", "push", f"https://github.com/{SOURCE_REPO}.git",
            f"{revision}:refs/heads/{SOURCE_BRANCH}", cwd=tmp,
            env=github_push_env(os.environ["GITHUB_TOKEN"]), capture=False)


def package_info() -> dict:
    return json.loads(
        run(
            "nix", "eval", "--impure", "--json", "--file", "packages.nix", "--apply",
            'builtins.mapAttrs (name: p: { path = toString p.out; version = p.version or "unknown"; preferLocalBuild = p.preferLocalBuild or false; allowSubstitutes = p.allowSubstitutes or true; })',
        )
    )


def resolve(revision: str) -> None:
    cache()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid source revision")
    proof = published()
    build_needed = (
        proof.get("revision") != revision
        or proof.get("clientDigest") != client_digest()
    )
    names = []
    if build_needed:
        snapshot(revision)
        names = sorted(package_info())
        required = {
            "cosmic-comp", "cosmic-session", "cosmic-greeter",
            "cosmic-panel", "cosmic-settings", "xdg-desktop-portal-cosmic",
        }
        if not required <= set(names) or len(names) > 100:
            raise RuntimeError("Unexpected COSMIC package set")

    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write("revision=" + revision + "\n")
        out.write("matrix=" + json.dumps(names, separators=(",", ":")) + "\n")
        out.write("build=" + ("true" if build_needed else "false") + "\n")
    print(
        f"Resolved {len(names)} package outputs at {revision}; "
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


def push_path(root: str) -> None:
    if not re.fullmatch(r"/nix/store/[0-9a-z]{32}-[^/\s]+", root):
        raise ValueError("Invalid runtime store path")
    if not os.environ.get("CACHIX_AUTH_TOKEN"):
        raise RuntimeError("CACHIX_AUTH_TOKEN is not configured")
    run("nix", "run", "github:NixOS/nixpkgs/nixos-unstable#cachix", "--", "push",
        cache()["name"], *shared.PUSH_OPTIONS, root, capture=False)


def push() -> None:
    push_path(Path("built-output.txt").read_text().strip())


def proof_for(revision: str) -> dict:
    snapshot(revision)
    info = package_info()
    if any(p["preferLocalBuild"] not in (False, "", "0", None)
           or p["allowSubstitutes"] in (False, "", "0", None) for p in info.values()):
        raise RuntimeError("A source package prevents normal substitution; refuse publication")
    return {
        "schema": 3,
        "revision": revision,
        "clientDigest": client_digest(),
        "builderRevision": os.environ["GITHUB_SHA"],
        "packages": info,
    }


def fetch_packages() -> None:
    run(
        "nix-build", "--expr",
        "builtins.map (p: p.out) (builtins.attrValues (import ./packages.nix))",
        "--no-out-link", "--max-jobs", "0", "--option", "builders", "",
        *options(), capture=False,
    )


def reference(host: dict) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", host["revision"]):
        raise ValueError("Invalid reference Nixpkgs revision")
    expression = (
        '(import ./check.nix) { host = fetchTarball { url = '
        + json.dumps("https://github.com/NixOS/nixpkgs/archive/" + host["revision"] + ".tar.gz")
        + '; sha256 = ' + json.dumps(host["sha256"]) + '; }; }'
    )
    return json.loads(run("nix", "eval", "--impure", "--json", "--expr", expression))


def build_reference(revision: str) -> None:
    proof = proof_for(revision)
    dump("cache-proof.json", proof)
    fetch_packages()
    sha = run("git", "ls-remote", "--exit-code", "https://github.com/NixOS/nixpkgs.git", "refs/heads/nixos-unstable").split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid nixos-unstable revision")
    host = {"revision": sha, "sha256": run("nix-prefetch-url", "--unpack", "https://github.com/NixOS/nixpkgs/archive/" + sha + ".tar.gz")}
    system = reference(host)
    run("nix-build", system["systemDerivation"], "--no-out-link", "--max-jobs", "1", "--cores", "2", *options(), capture=False)
    system["closurePaths"] = len(run("nix-store", "-qR", system["systemPath"]).splitlines())
    dump("reference-systems.json", {
        "revision": revision, "clientDigest": client_digest(),
        "builderRevision": os.environ["GITHUB_SHA"],
        "systems": {"nixos-unstable": {**host, **system}},
    })


def push_reference() -> None:
    data = json.loads(Path("reference-systems.json").read_text())
    for system in data["systems"].values():
        push_path(system["systemPath"])


def validate_proof(proof: dict, evaluate: bool = True) -> None:
    snap = json.loads(Path("snapshot.json").read_text())
    if (proof.get("schema") != 3 or proof.get("clientDigest") != client_digest()
            or proof.get("builderRevision") != os.environ.get("GITHUB_SHA")
            or snap != {"schema": 2, "url": f"github:{SOURCE_REPO}/{proof['revision']}"}
            or not proof.get("verifiedAt") or not proof.get("referenceSystems")
            or not proof.get("packages")
            or (evaluate and proof["packages"] != package_info())):
        raise RuntimeError("Stale or incomplete cache proof; refuse publication")


def verify(revision: str) -> None:
    Path("cache-proof.json").unlink(missing_ok=True)
    try:
        proof = proof_for(revision)
        fetch_packages()
        data = json.loads(Path("reference-systems.json").read_text())
        if any(data.get(k) != proof[k] for k in ("revision", "clientDigest", "builderRevision")):
            raise RuntimeError("Reference system provenance does not match this build")
        if set(data["systems"]) != {"nixos-unstable"}:
            raise RuntimeError("Missing required reference system")
        dump("cache-proof.json", proof)
        for host in data["systems"].values():
            result = reference(host)
            if any(result[k] != host[k] for k in result):
                raise RuntimeError("Reference system output changed during verification")
            run("nix-store", "--realise", host["systemPath"], "--option", "max-jobs", "0",
                "--option", "builders", "", *options(), capture=False)
            if len(run("nix-store", "-qR", host["systemPath"]).splitlines()) != host["closurePaths"]:
                raise RuntimeError("Reference system closure is incomplete")
        proof.update(
            verifiedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            method="Fresh runner: complete runtime and reference closures fetched with all builders disabled; exact module/package/system identity",
            referenceSystems=data["systems"],
        )
        dump("cache-proof.json", proof)
        validate_proof(proof)
    except Exception:
        Path("cache-proof.json").unlink(missing_ok=True)
        raise
    print("COSMIC runtime and complete NixOS reference system verified without compilation")


def retention_root(previous_roots: list[str]) -> str:
    if previous_roots:
        run("nix-store", "--realise", *previous_roots, "--option", "max-jobs", "0",
            "--option", "builders", "", *options(), capture=False)
    root = run("nix-build", "retention-root.nix", "--no-out-link",
               "--arg", "previousRoots", "builtins.fromJSON " + json.dumps(json.dumps(previous_roots)),
               *options())
    return root


def pin_root(root: str) -> None:
    if not re.fullmatch(r"/nix/store/[0-9a-z]{32}-[^/\s]+", root):
        raise ValueError("Invalid retention root")
    run("nix-store", "--realise", root, "--option", "max-jobs", "0",
        "--option", "builders", "", *options(), capture=False)
    push_path(root)
    run("nix", "run", "github:NixOS/nixpkgs/nixos-unstable#cachix", "--", "pin",
        cache()["name"], "cosmic-x86_64-linux", root, "--keep-revisions", "1", capture=False)


def pin(previous_roots: list[str]) -> None:
    pin_root(retention_root(previous_roots))


def retain() -> None:
    from scripts.storage import check, roots
    proof = json.loads(Path("cache-proof.json").read_text())
    validate_proof(proof)
    previous = published()
    report = check(candidate=True, published=previous)
    current_root = retention_root([])
    push_path(current_root)
    pin(sorted(roots(previous)) if previous else [])
    proof["retentionRoot"] = current_root
    proof["publicationParent"] = previous.get("publicationRevision", "")
    proof["storage"] = {k: v for k, v in report.items() if k != "paths"}
    dump("cache-proof.json", proof)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["update-source", "publish-source", "resolve", "build", "push", "reference", "push-reference", "verify", "retain", "publish"],
    )
    parser.add_argument("--revision", default=os.environ.get("SOURCE_REV", ""))
    parser.add_argument("--package", default=os.environ.get("PACKAGE", ""))
    args = parser.parse_args()
    {
        "update-source": update_source,
        "publish-source": lambda: publish_source(args.revision),
        "resolve": lambda: resolve(args.revision),
        "build": lambda: build(args.package, args.revision),
        "push": push,
        "reference": lambda: build_reference(args.revision),
        "push-reference": push_reference,
        "verify": lambda: verify(args.revision),
        "retain": retain,
        "publish": publish,
    }[args.command]()


if __name__ == "__main__":
    try:
        os.chdir(Path(__file__).resolve().parent)
        main()
    except (
        subprocess.SubprocessError,
        ValueError,
        RuntimeError,
        KeyError,
        OSError,
        urllib.error.URLError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
