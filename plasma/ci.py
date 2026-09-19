#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
from graphlib import TopologicalSorter
from concurrent.futures import ThreadPoolExecutor
import re
import subprocess
import sys
import urllib.request

from scripts import cache as shared
from scripts.cache import cache, dump, options, run

NIXPKGS = "NixOS/nixpkgs"
PULL_REQUEST = int(os.environ.get("PLASMA_PR", "561955"))
STAGES = 5
CLIENT_FILES = [
    ".github/workflows/plasma-build.yml",
    ".github/workflows/plasma.yml",
    "cache.json",
    "plasma/ci.py",
    "plasma/check-integration.nix",
    "plasma/default.nix",
    "plasma/packages.nix",
    "plasma/profile.nix",
    "plasma/retention-root.nix",
    "scripts/cache.py",
]


def client_digest() -> str:
    return shared.client_digest(CLIENT_FILES)


def published() -> dict:
    return shared.published("plasma-cache", "plasma")


def publish() -> None:
    shared.publish("plasma-cache")


def github_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def tarball(revision: str) -> str:
    return f"https://github.com/{NIXPKGS}/archive/{revision}.tar.gz"


def tree(revision: str, sha256: str) -> str:
    return f'(fetchTarball {{ url = "{tarball(revision)}"; sha256 = "{sha256}"; }})'


def snapshot(revision: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid nixpkgs revision")
    existing = Path("snapshot.json")
    if existing.is_file():
        value = json.loads(existing.read_text())
        if value.get("revision") == revision:
            return value
    sha256 = run("nix-prefetch-url", "--unpack", tarball(revision))
    t = tree(revision, sha256)
    version = run(
        "nix", "eval", "--impure", "--raw", "--expr",
        f'(import {t} {{ system = "x86_64-linux"; }}).kdePackages.plasma-workspace.version',
    )
    if not re.fullmatch(r"6\.[0-9]+\.[0-9]+", version):
        raise RuntimeError(f"Unexpected Plasma version {version!r}")
    # Every kdePackages attribute at the Plasma version, and the subset the
    # NixOS plasma6 module installs (a container evaluation, nothing built).
    expression = (
        f'let pkgs = import {t} {{ system = "x86_64-linux"; }}; '
        f'c = (import ({t} + "/nixos") {{ system = "x86_64-linux"; configuration = ./profile.nix; }}).config; '
        'installed = map (p: if builtins.isAttrs p then p.outPath or "" else "") '
        '(c.environment.systemPackages ++ c.xdg.portal.extraPortals); '
        'ks = pkgs.kdePackages; '
        'plasma = builtins.filter (n: let r = builtins.tryEval (ks.${n}.version or ""); '
        f'in r.success && r.value == "{version}") (builtins.attrNames ks); '
        f'projects = builtins.fromJSON (builtins.readFile ({t} + "/pkgs/kde/generated/projects.json")); '
        'in { inherit plasma; selected = builtins.filter (n: builtins.elem ks.${n}.outPath installed) plasma; '
        'projects = builtins.listToAttrs (map (name: { inherit name; value = projects.${name}.repo_path; }) plasma); '
        'dependencies = { qt = pkgs.qt6.qtbase.version; frameworks = ks.kcoreaddons.version; }; }'
    )
    sets = json.loads(run("nix", "eval", "--impure", "--json", "--expr", expression))
    if not {"kwin", "plasma-workspace", "plasma-desktop"} <= set(sets["selected"]):
        raise RuntimeError("The plasma6 module no longer installs the core packages")
    value = {
        "schema": 2,
        "revision": revision,
        "url": tarball(revision),
        "sha256": sha256,
        "version": version,
        "plasma": sorted(sets["plasma"]),
        "projects": sets["projects"],
        "dependencies": sets["dependencies"],
        "selected": sorted(sets["selected"]),
    }
    dump("snapshot.json", value)
    return value


def source_revision() -> str:
    override = os.environ.get("SOURCE_REV_OVERRIDE", "").strip()
    if override:
        if not re.fullmatch(r"[0-9a-f]{40}", override):
            raise ValueError("SOURCE_REV_OVERRIDE must be a full nixpkgs commit")
        return override
    pull = github_json(f"https://api.github.com/repos/{NIXPKGS}/pulls/{PULL_REQUEST}")
    if pull.get("state") != "open":
        return github_json(f"https://api.github.com/repos/{NIXPKGS}/commits/nixos-unstable")["sha"]
    return pull["head"]["sha"]


def batches(dependencies: dict[str, set[str]]) -> list[list[list[str]]]:
    """Pack the DAG into five waves; dependent packages share a runner within a wave."""
    depths: dict[str, int] = {}
    for name in TopologicalSorter(dependencies).static_order():
        depths[name] = 1 + max((depths[d] for d in dependencies[name]), default=-1)
    height = max(depths.values(), default=0) + 1
    waves: list[list[list[str]]] = [[] for _ in range(STAGES)]
    for wave in range(STAGES):
        remaining = {n for n, depth in depths.items() if depth * STAGES // height == wave}
        # Connected components keep every dependency within its runner or an earlier wave.
        while remaining:
            component = {min(remaining)}
            while True:
                connected = component | {
                    n for n in remaining
                    if dependencies[n] & component
                    or any(n in dependencies[c] for c in component)
                }
                if connected == component:
                    break
                component = connected
            waves[wave].append(sorted(component))
            remaining -= component
    return waves


def levels(value: dict) -> list[list[list[str]]]:
    drvs = json.loads(run(
        "nix", "eval", "--impure", "--json", "--file", "packages.nix",
        "--apply", "p: builtins.mapAttrs (_: d: d.drvPath) p.plasma",
    ))
    # Several attributes can name the same derivation: schedule it only once.
    by_drv = {d: n for n, d in sorted(drvs.items(), reverse=True)}
    closures = {}
    pending = {by_drv[drvs[n]] for n in value["selected"]}
    while pending:
        name = min(pending)
        closure = set(run("nix-store", "-qR", drvs[name]).split())
        closures[name] = {by_drv[d] for d in closure if d in by_drv} - {name}
        pending = (pending | closures[name]) - closures.keys()
    value["needed"] = sorted(closures)
    return batches(closures)


def git_heads(projects: dict[str, str]) -> dict[str, dict]:
    def head(item):
        name, project = item
        url = f"https://invent.kde.org/{project}"
        result = run("git", "ls-remote", "--symref", url + ".git", "HEAD")
        revision = next((line.split()[0] for line in result.splitlines() if line.endswith("\tHEAD") and not line.startswith("ref:")), "")
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise RuntimeError(f"Cannot resolve {project} HEAD")
        return name, {"revision": revision, "url": f"{url}/-/archive/{revision}/{name}-{revision}.tar.gz"}
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(head, sorted(projects.items())))


def git_sources(heads: dict[str, dict], previous: dict, value: dict) -> dict:
    def fetch(item):
        name, source = item
        old = previous.get(name, {})
        if old.get("revision") == source["revision"] and old.get("url") == source["url"]:
            return name, old
        sha256, path = run("nix-prefetch-url", "--unpack", "--name", "source", "--print-path", source["url"]).splitlines()
        cmake = Path(path, "CMakeLists.txt")
        text = cmake.read_text() if cmake.exists() else ""
        version = re.search(r'(?:set\s*\(\s*(?:PROJECT_VERSION|PLASMA_VERSION)|project\s*\(\s*\S+\s+VERSION)\s+"?([0-9]+\.[0-9]+\.[0-9]+)', text, re.IGNORECASE)
        if name in ("kwin", "plasma-workspace"):
            for key, variable in (("qt", "QT_MIN_VERSION"), ("frameworks", "KF6_MIN_VERSION")):
                minimum = re.search(r'set\s*\(\s*' + variable + r'\s+"?([0-9.]+)', text)
                if minimum and tuple(map(int, value["dependencies"][key].split("."))) < tuple(map(int, minimum[1].split("."))):
                    raise RuntimeError(f"{name} Git needs {key} {minimum[1]}, packaging provides {value['dependencies'][key]}")
        return name, {**source, "sha256": sha256, "version": (version[1] if version else value["version"]) + "-git." + source["revision"][:12]}
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(fetch, sorted(heads.items())))


def write_matrix(revision: str, stages: list, build_needed: bool) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write("revision=" + revision + "\n")
        for i, groups in enumerate(stages):
            out.write(f"l{i}=" + json.dumps(groups, separators=(",", ":")) + "\n")
        out.write("build=" + ("true" if build_needed else "false") + "\n")


def resume() -> None:
    """Reuse an interrupted run's immutable snapshot, never refresh its Git heads."""
    cache()
    value = json.loads(Path("snapshot.json").read_text())
    revision = value["revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or value["url"] != tarball(revision):
        raise ValueError("Invalid checkpoint packaging revision")
    mode = value["mode"]
    sources = value.get("gitSources", {})
    if mode not in ("git", "beta") or (mode == "git" and set(sources) != set(value["projects"])):
        raise ValueError("Incomplete checkpoint sources")
    heads = {name: {key: source[key] for key in ("revision", "url")}
             for name, source in sources.items()}
    digest = hashlib.sha256(json.dumps(heads, sort_keys=True).encode()).hexdigest()
    if digest != value["sourceDigest"]:
        raise ValueError("Checkpoint source digest does not match")
    stages = levels(value)
    if len(value["needed"]) > 120:
        raise RuntimeError("Unexpected checkpoint package matrix size")
    dump("snapshot.json", value)
    write_matrix(revision, stages, True)
    print(f"Resuming immutable Plasma {mode} snapshot {digest}: {len(value['needed'])} packages")


def resolve() -> None:
    cache()
    proof = published()
    revision = source_revision()
    build_needed = (
        proof.get("revision") != revision
        or proof.get("clientDigest") != client_digest()
    )
    previous = proof.get("snapshot", {})
    if not build_needed and previous.get("projects"):
        value = previous.copy()
    else:
        value = snapshot(revision)
    mode = os.environ.get("SOURCE_MODE", "git") or "git"
    if mode not in ("git", "beta"):
        raise ValueError("SOURCE_MODE must be git or beta")
    heads = git_heads(value["projects"]) if mode == "git" else {}
    source_digest = hashlib.sha256(json.dumps(heads, sort_keys=True).encode()).hexdigest()
    build_needed |= proof.get("sourceDigest") != source_digest or proof.get("mode") != mode
    stages = [[] for _ in range(STAGES)]
    if build_needed:
        value["mode"] = mode
        value["sourceDigest"] = source_digest
        reusable = previous.get("gitSources", {}) if previous.get("dependencies") == value["dependencies"] else {}
        value["gitSources"] = git_sources(heads, reusable, value)
        dump("snapshot.json", value)
        stages = levels(value)
        if len(value["needed"]) > 120:
            raise RuntimeError("Unexpected package matrix size")
        dump("snapshot.json", value)
        print(f"Plasma {mode} at nixpkgs {revision}: batches {[len(s) for s in stages]}")
    write_matrix(revision, stages, build_needed)
    print(f"Build needed: {build_needed}")


def build(names: list[str], revision: str) -> None:
    value = snapshot(revision)
    if not names or not set(names) <= set(value["needed"]):
        raise ValueError("Expected a nonempty batch of snapshot packages")
    attributes = [arg for name in names for arg in ("-A", "outputs." + name)]
    built = run(
        "nix-build", "packages.nix", *attributes, "--no-out-link",
        "--max-jobs", "1", *options(),
    ).splitlines()
    if not built or not all(re.fullmatch(r"/nix/store/[0-9a-z]{32}-[^\s]+", p) for p in built):
        raise RuntimeError("Expected store outputs")
    Path("built-output.txt").write_text("\n".join(dict.fromkeys(built)) + "\n")


def push() -> None:
    paths = Path("built-output.txt").read_text().split()
    if not os.environ.get("CACHIX_AUTH_TOKEN"):
        raise RuntimeError("CACHIX_AUTH_TOKEN is not configured")
    run("nix", "run", "--file", "packages.nix", "cachix", "--", "push", cache()["name"], *shared.PUSH_OPTIONS, *paths, capture=False)


def package_info() -> dict:
    return json.loads(run(
        "nix", "eval", "--impure", "--json", "--file", "packages.nix", "--apply",
        'p: builtins.mapAttrs (name: d: { path = toString d.out; version = d.version or "unknown"; '
        'preferLocalBuild = d.preferLocalBuild or false; }) p.selected',
    ))


def verify(revision: str) -> None:
    value = snapshot(revision)
    info = package_info()
    if any(p["preferLocalBuild"] not in (False, "", "0", None) for p in info.values()):
        raise RuntimeError("A source package forces local builds; refuse publication")

    expression = "builtins.concatLists (builtins.attrValues (import ./packages.nix).outputs)"
    run(
        "nix-build", "--expr", expression, "--no-out-link", "--max-jobs", "0",
        "--option", "builders", "", *options(), capture=False,
    )

    dump(
        "cache-proof.json",
        {
            "schema": 2,
            "verifiedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "revision": revision,
            "version": info["plasma-workspace"]["version"],
            "mode": value["mode"],
            "sourceDigest": value["sourceDigest"],
            "clientDigest": client_digest(),
            "builderRevision": os.environ["GITHUB_SHA"],
            "method": (
                "fresh-job nix-build: max-jobs=0, no remote builders; "
                "all non-debug outputs of required Plasma packages; exact module-output equality"
            ),
            "packages": info,
        },
    )
    try:
        # Consumers have their own Nixpkgs. Check the complete system with both
        # the packaging tree and a separate current host, not just lazy assertions.
        host_revision = github_json(f"https://api.github.com/repos/{NIXPKGS}/commits/nixos-unstable")["sha"]
        host_hash = run("nix-prefetch-url", "--unpack", tarball(host_revision))
        hosts = {"packaging": (revision, value["sha256"]), "nixos-unstable": (host_revision, host_hash)}
        checks = {}
        for name, (host_rev, host_sha256) in hosts.items():
            result = json.loads(run(
                "nix", "eval", "--impure", "--json", "--expr",
                f'(import ./check-integration.nix) {{ hostNixpkgs = {tree(host_rev, host_sha256)}; }}',
            ))
            checks[name] = {"revision": host_rev, "sha256": host_sha256, **result}
        proof = json.loads(Path("cache-proof.json").read_text())
        proof["integrationChecks"] = checks
        proof["method"] += "; full NixOS system evaluation on packaging and nixos-unstable hosts"
        dump("cache-proof.json", proof)
    except Exception:
        Path("cache-proof.json").unlink()
        raise

    print("Cached outputs, module-output identity and complete NixOS system evaluations verified")


def retain() -> None:
    root = run("nix-build", "retention-root.nix", "--no-out-link", *options())
    c = cache()["name"]
    run("nix", "run", "--file", "packages.nix", "cachix", "--", "push", c, *shared.PUSH_OPTIONS, root, capture=False)
    run(
        "nix", "run", "--file", "packages.nix", "cachix", "--", "pin", c,
        "plasma-x86_64-linux", root, "--keep-revisions", "1", capture=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["resolve", "resume", "build", "push", "verify", "retain", "publish"])
    parser.add_argument("--revision", default=os.environ.get("SOURCE_REV", ""))
    parser.add_argument("--packages", default=os.environ.get("PACKAGES", "[]"))
    args = parser.parse_args()
    {
        "resolve": resolve,
        "resume": resume,
        "build": lambda: build(json.loads(args.packages), args.revision),
        "push": push,
        "verify": lambda: verify(args.revision),
        "retain": retain,
        "publish": publish,
    }[args.command]()


if __name__ == "__main__":
    try:
        os.chdir(Path(__file__).resolve().parent)
        main()
    except (subprocess.SubprocessError, ValueError, RuntimeError, KeyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
