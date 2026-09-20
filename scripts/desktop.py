"""Runtime-only build, fresh-cache verification and retention for scoped desktops."""
import datetime
import json
import os
import subprocess
from pathlib import Path
import urllib.request
from scripts import cache as shared
from scripts.cache import dump, options, run


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def tree(revision, sha256):
    return f'(fetchTarball {{ url = "https://github.com/NixOS/nixpkgs/archive/{revision}.tar.gz"; sha256 = "{sha256}"; }})'


def info():
    return json.loads(run("nix", "eval", "--impure", "--json", "--file", "packages.nix", "--apply", 'p: { packages = builtins.mapAttrs (_: d: { path = toString d.out; version = d.version; }) p.desktop; runtimePaths = map toString p.runtime; }'))


def proof(digest):
    snapshot = json.loads(Path("snapshot.json").read_text())
    return {"schema": 1, "mode": "git", "revision": snapshot["revision"], "sourceDigest": snapshot["sourceDigest"], "clientDigest": digest(), "builderRevision": os.environ["GITHUB_SHA"], **info()}


def integration(revision, sha256):
    return json.loads(run("nix", "eval", "--impure", "--json", "--expr", f'(import ./check-integration.nix) {{ hostNixpkgs = {tree(revision, sha256)}; }}'))


def build(digest):
    value = proof(digest)
    dump("cache-proof.json", value)
    host = fetch("https://api.github.com/repos/NixOS/nixpkgs/commits/nixos-unstable")["sha"]
    host_hash = run("nix-prefetch-url", "--unpack", f"https://github.com/NixOS/nixpkgs/archive/{host}.tar.gz")
    result = integration(host, host_hash)
    run("nix-build", "packages.nix", "-A", "runtime", "--no-out-link", "--max-jobs", "1", "--cores", "2", *options(), capture=False)
    built = run("nix-build", result["systemDerivation"], "--no-out-link", "--max-jobs", "1", "--cores", "2", *options())
    if built != result["systemPath"]:
        raise RuntimeError("Reference system output differs")
    dump("reference-systems.json", {"sourceDigest": value["sourceDigest"], "clientDigest": value["clientDigest"], "systems": {"nixos-unstable": {"revision": host, "sha256": host_hash, **result, "closurePaths": len(run("nix-store", "-qR", built).split())}}})


def push():
    if not os.environ.get("CACHIX_AUTH_TOKEN"):
        raise RuntimeError("CACHIX_AUTH_TOKEN is not configured")
    systems = json.loads(Path("reference-systems.json").read_text())["systems"]
    paths = info()["runtimePaths"] + [s["systemPath"] for s in systems.values()]
    run("nix", "run", "--file", "packages.nix", "cachix", "--", "push", shared.cache()["name"], *shared.PUSH_OPTIONS, *paths, capture=False)


def salvage():
    """Keep completed runtimes from a failed build, without publishing or pinning."""
    paths = []
    for path in info()["runtimePaths"]:
        try:
            run("nix-store", "--check-validity", path)
        except subprocess.CalledProcessError:
            continue
        paths.append(path)
    if paths:
        run("nix", "run", "--file", "packages.nix", "cachix", "--", "push", shared.cache()["name"], *shared.PUSH_OPTIONS, *paths, capture=False)


def verify(digest):
    run("nix-build", "packages.nix", "-A", "runtime", "--no-out-link", "--max-jobs", "0", "--option", "builders", "", *options(), capture=False)
    value = proof(digest)
    dump("cache-proof.json", value)
    try:
        references = json.loads(Path("reference-systems.json").read_text())
        if references["sourceDigest"] != value["sourceDigest"] or references["clientDigest"] != value["clientDigest"]:
            raise RuntimeError("Reference systems differ from source/client snapshot")
        for name, system in references["systems"].items():
            result = integration(system["revision"], system["sha256"])
            if any(result[key] != system[key] for key in result):
                raise RuntimeError("Reference evaluation differs")
            run("nix-store", "--realise", system["systemPath"], "--max-jobs", "0", "--option", "builders", "", *options(), capture=False)
            if len(run("nix-store", "-qR", system["systemPath"]).split()) != system["closurePaths"]:
                raise RuntimeError("Reference closure differs")
        value["referenceSystems"] = references["systems"]
        value["verifiedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        value["method"] = "fresh runner, runtime outputs and complete reference closure fetched with local/remote builds disabled; native application identities"
        dump("cache-proof.json", value)
    except Exception:
        Path("cache-proof.json").unlink()
        raise


def retain(desktop):
    from scripts.storage import check
    report = check(desktop)
    value = json.loads(Path("cache-proof.json").read_text())
    value["storage"] = {k: v for k, v in report.items() if k != "paths"}
    dump("cache-proof.json", value)
    root = run("nix-build", "retention-root.nix", "--no-out-link", *options())
    c = shared.cache()["name"]
    run("nix", "run", "--file", "packages.nix", "cachix", "--", "push", c, *shared.PUSH_OPTIONS, root, capture=False)
    run("nix", "run", "--file", "packages.nix", "cachix", "--", "pin", c, f"{desktop}-x86_64-linux", root, "--keep-revisions", "1", capture=False)

