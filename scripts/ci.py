#!/usr/bin/env python3
"""Resolve, build, publish and verify COSMIC cache snapshots in GitHub Actions."""
from __future__ import annotations
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

UPSTREAM = "github:amozeo/nixos-cosmic/main"


def run(*args: str, capture: bool = True) -> str:
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def dump(path: str, value: object) -> None:
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def cache() -> dict:
    value = json.loads(Path("cache.json").read_text())
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", value["name"]):
        raise ValueError("Invalid cache name")
    expected = f'https://{value["name"]}.cachix.org'
    if value["uri"].rstrip("/") != expected:
        raise ValueError("Unexpected Cachix URL")
    keys = value.get("publicSigningKeys", [])
    if not keys or not all(isinstance(k, str) and k.startswith(value["name"] + ".cachix.org-") for k in keys):
        raise ValueError("Missing/invalid cache public signing keys")
    return value


def options() -> list[str]:
    c = cache()
    return ["--option", "extra-substituters", c["uri"],
            "--option", "extra-trusted-public-keys", " ".join(c["publicSigningKeys"]),
            "--option", "narinfo-cache-negative-ttl", "0",
            "--option", "fallback", "false"]


def snapshot(revision: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid upstream revision")
    dump("snapshot.json", {"schema": 1, "url": f"github:amozeo/nixos-cosmic/{revision}"})


def package_info() -> dict:
    return json.loads(run("nix", "eval", "--impure", "--json", "--file", "packages.nix", "--apply",
        'builtins.mapAttrs (name: p: { path = toString p.out; version = p.version or "unknown"; preferLocalBuild = p.preferLocalBuild or false; })'))


def resolve() -> None:
    cache()
    meta = json.loads(run("nix", "flake", "metadata", "--refresh", "--json", UPSTREAM))
    revision = meta["locked"]["rev"]
    snapshot(revision)
    names = sorted(package_info())
    required = {"cosmic-comp", "cosmic-session", "cosmic-greeter", "cosmic-panel", "cosmic-settings", "xdg-desktop-portal-cosmic"}
    if not required <= set(names):
        raise RuntimeError("Upstream is missing required COSMIC packages")
    if not names or len(names) > 100:
        raise RuntimeError("Unexpected package matrix size")
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write("revision=" + revision + "\n")
        out.write("matrix=" + json.dumps(names, separators=(",", ":")) + "\n")
    print(f"Resolved {len(names)} package outputs at {revision}")


def build(name: str, revision: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Invalid package name")
    snapshot(revision)
    root = run("nix-build", "packages.nix", "-A", name + ".out", "--no-out-link",
               "--cores", "2", "--max-jobs", "1", *options())
    if not re.fullmatch(r"/nix/store/[0-9a-z]{32}-[^\s]+", root):
        raise RuntimeError("Expected exactly one store output")
    Path("built-output.txt").write_text(root + "\n")
    print(root)


def push() -> None:
    root = Path("built-output.txt").read_text().strip()
    if not os.environ.get("CACHIX_AUTH_TOKEN"):
        raise RuntimeError("CACHIX_AUTH_TOKEN is not configured")
    run("nix", "run", "nixpkgs#cachix", "--", "push", cache()["name"], root, capture=False)


def verify(revision: str) -> None:
    snapshot(revision)
    info = package_info()
    # A fresh job must obtain these package outputs by substitution, not build them.
    if any(p["preferLocalBuild"] not in (False, "", "0", None) for p in info.values()):
        raise RuntimeError("An upstream package forces local builds; refuse publication")
    expression = "builtins.map (p: p.out) (builtins.attrValues (import ./packages.nix))"
    run("nix-build", "--expr", expression, "--no-out-link", "--max-jobs", "0",
        "--option", "builders", "", *options(), capture=False)
    # Check the module selects the exact outputs just tested, independent of host pkgs.
    expression = '''let
      s = builtins.fromJSON (builtins.readFile ./snapshot.json);
      u = builtins.getFlake s.url;
      n = u.inputs.nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [ ./default.nix ({ ... }: {
          boot.isContainer = true;
          services.desktopManager.cosmic.enable = true;
          services.displayManager.cosmic-greeter.enable = true;
          system.stateVersion = "25.11";
        }) ];
      };
      p = import ./packages.nix;
    in builtins.all (name: n.pkgs.${name}.outPath == p.${name}.outPath) (builtins.attrNames p)'''
    if run("nix", "eval", "--impure", "--json", "--expr", expression) != "true":
        raise RuntimeError("NixOS integration changed the cached package outputs")
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dump("cache-proof.json", {"schema": 1, "verifiedAt": stamp, "revision": revision,
         "method": "fresh-job nix-build: max-jobs=0, no remote builders; exact module-output equality",
         "packages": info})
    print("Cached package outputs and module-output identity verified")


def retain() -> None:
    # This creates a tiny text root on CI, not a desktop compilation on the laptop.
    root = run("nix-build", "retention-root.nix", "--no-out-link", *options())
    c = cache()["name"]
    run("nix", "run", "nixpkgs#cachix", "--", "push", c, root, capture=False)
    run("nix", "run", "nixpkgs#cachix", "--", "pin", c, "cosmic-x86_64-linux", root,
        "--keep-revisions", "2", capture=False)


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
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "snapshot.json", "cache-proof.json")
    tree = run("git", "write-tree")
    sha = run("git", "commit-tree", tree, "-p", parent, "-m", "Publish verified COSMIC cache snapshot")
    run("git", "push", "origin", sha + ":refs/heads/cached", capture=False)
    print("Published cached branch: " + sha)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["resolve", "build", "push", "verify", "retain", "publish"])
    parser.add_argument("--revision", default=os.environ.get("SOURCE_REV", ""))
    parser.add_argument("--package", default=os.environ.get("PACKAGE", ""))
    args = parser.parse_args()
    {"resolve": resolve, "build": lambda: build(args.package, args.revision), "push": push,
     "verify": lambda: verify(args.revision), "retain": retain, "publish": publish}[args.command]()


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, ValueError, RuntimeError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
