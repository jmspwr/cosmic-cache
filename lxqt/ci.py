#!/usr/bin/env python3
"""Resolve the LXQt desktop from immutable commits on upstream default branches."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from scripts import cache as shared
from scripts import desktop as lifecycle
from scripts.cache import dump, run

PROJECTS = [
    "lxqt-build-tools", "libqtxdg", "libsysstat", "liblxqt", "qtxdg-tools",
    "libdbusmenu-lxqt", "libfm-qt", "lxqt-about", "lxqt-admin", "lxqt-config",
    "lxqt-globalkeys", "lxqt-menu-data", "lxqt-notificationd", "lxqt-openssh-askpass",
    "lxqt-policykit", "lxqt-powermanagement", "lxqt-qtplugin", "lxqt-session",
    "lxqt-sudo", "lxqt-themes", "lxqt-wayland-session", "pavucontrol-qt",
    "lxqt-panel", "lxqt-runner", "pcmanfm-qt", "xdg-desktop-portal-lxqt",
]
CLIENT_FILES = [".github/workflows/desktops.yml", ".github/workflows/lxqt.yml", "cache.json",
    "scripts/cache.py", "scripts/storage.py", "scripts/integration.py", "checks/combined.nix", "scripts/desktop.py"] + ["lxqt/" + p for p in
    ["ci.py", "packages.nix", "default.nix", "profile.nix", "check-integration.nix", "retention-root.nix"]]


def digest():
    return shared.client_digest(CLIENT_FILES)


def head(repo):
    revision = run("git", "ls-remote", f"https://github.com/lxqt/{repo}.git", "HEAD").split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError(f"Invalid Git revision for {repo}")
    return revision


def resolve():
    revision = lifecycle.fetch("https://api.github.com/repos/NixOS/nixpkgs/commits/nixos-unstable")["sha"]
    previous = shared.published("lxqt-cache", "lxqt")
    old = previous.get("snapshot", {})
    with ThreadPoolExecutor(max_workers=6) as pool:
        heads = dict(pool.map(lambda n: (n, head(n)), PROJECTS))
    source_digest = hashlib.sha256(json.dumps(heads, sort_keys=True).encode()).hexdigest()
    changed = previous.get("sourceDigest") != source_digest or previous.get("revision") != revision or previous.get("clientDigest") != digest()
    if changed:
        url = f"https://github.com/NixOS/nixpkgs/archive/{revision}.tar.gz"
        sha256 = old["sha256"] if old.get("revision") == revision else run("nix-prefetch-url", "--unpack", url)
        def source(name):
            rev = heads[name]
            cached = old.get("sources", {}).get(name, {})
            if cached.get("revision") == rev:
                return name, cached
            url = f"https://github.com/lxqt/{name}/archive/{rev}.tar.gz"
            return name, {"revision": rev, "url": url, "sha256": run("nix-prefetch-url", "--unpack", url)}
        with ThreadPoolExecutor(max_workers=4) as pool:
            sources = dict(pool.map(source, PROJECTS))
        dump("snapshot.json", {"schema": 1, "mode": "git", "revision": revision, "url": url, "sha256": sha256, "sourceDigest": source_digest, "sources": sources})
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write("build=" + str(changed).lower() + "\n")
    print(f"LXQt Git: {len(heads)} desktop sources; build={changed}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["resolve", "build", "push", "verify", "retain", "publish", "salvage"])
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parent)
    {"resolve": resolve, "build": lambda: lifecycle.build(digest), "push": lifecycle.push, "salvage": lifecycle.salvage,
     "verify": lambda: lifecycle.verify(digest), "retain": lambda: lifecycle.retain("lxqt"),
     "publish": lambda: shared.publish("lxqt-cache")}[args.command]()


if __name__ == "__main__":
    main()
