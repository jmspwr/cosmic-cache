#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

from scripts import cache as shared
from scripts import desktop as lifecycle
from scripts.cache import dump, run

PR = 559510
PROJECTS = ["gjs", "gnome-control-center", "gnome-session", "gnome-settings-daemon", "gnome-shell", "gsettings-desktop-schemas", "mutter", "xdg-desktop-portal-gnome"]
CLIENT_FILES = [".github/workflows/desktops.yml", ".github/workflows/gnome.yml", "cache.json", "scripts/cache.py", "scripts/storage.py", "scripts/integration.py", "checks/combined.nix", "scripts/desktop.py"] + ["gnome/" + p for p in ["ci.py", "packages.nix", "default.nix", "profile.nix", "check-integration.nix", "retention-root.nix"]]


def digest():
    return shared.client_digest(CLIENT_FILES)


def fetch(url, decode=True):
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read().decode()
    return json.loads(data) if decode else data


def api(repo, suffix):
    return "https://gitlab.gnome.org/api/v4/projects/" + urllib.parse.quote("GNOME/" + repo, safe="") + "/repository/" + suffix


def archive(repo, revision, old=None):
    url = f"https://gitlab.gnome.org/GNOME/{repo}/-/archive/{revision}/{repo}-{revision}.tar.gz"
    if old and old.get("revision") == revision and old.get("url") == url:
        return {k: old[k] for k in ["revision", "url", "sha256"]}
    result = run("nix-prefetch-url", "--unpack", url).splitlines()[0]
    return {"revision": revision, "url": url, "sha256": result}


def source(repo, revision, old):
    if old.get("revision") == revision and old.get("sourceSchema") == 2:
        return old
    value = archive(repo, revision, old)
    value["sourceSchema"] = 2
    meson = fetch(api(repo, "files/meson.build/raw?ref=" + revision), False)
    version = re.search(r"\bversion\s*:\s*['\"]([^'\"]+)", meson)
    if not version:
        raise RuntimeError(f"Missing source version for {repo}")
    value["version"] = version[1]
    value["subprojects"] = []
    if repo in {"gjs", "gnome-settings-daemon", "gnome-control-center", "xdg-desktop-portal-gnome", "gnome-shell", "mutter"}:
        entries = fetch(api(repo, "tree?path=subprojects&per_page=100&ref=" + revision))
        for entry in entries:
            if entry["type"] == "commit":
                dependency = {"gvc": "libgnome-volume-control", "gobject-introspection-tests": "gobject-introspection-tests"}.get(entry["name"])
                if not dependency:
                    raise RuntimeError(f"Unrecognised submodule {repo}/{entry['name']}")
                value["subprojects"].append({"path": entry["path"], **archive(dependency, entry["id"])})
            elif entry["name"] in {"libgxdp.wrap", "gvdb.wrap", "libshew.wrap", "gvc.wrap"}:
                dependency = {"gvc.wrap": "libgnome-volume-control"}.get(entry["name"], entry["name"].removesuffix(".wrap"))
                wrap = configparser.ConfigParser()
                wrap.read_string(fetch(api(repo, "files/subprojects%2F" + entry["name"] + "/raw?ref=" + revision), False))
                ref = wrap["wrap-git"]["revision"]
                if not re.fullmatch(r"[0-9a-f]{40}", ref) or wrap["wrap-git"]["url"] != f"https://gitlab.gnome.org/GNOME/{dependency}.git":
                    raise RuntimeError(f"Unpinned or unexpected {entry['name']}")
                directory = wrap["wrap-git"].get("directory", entry["name"].removesuffix(".wrap"))
                if not re.fullmatch(r"[a-z][a-z0-9-]*", directory):
                    raise RuntimeError("Invalid subproject directory")
                value["subprojects"].append({"path": "subprojects/" + directory, **archive(dependency, ref)})
    return value


def resolve():
    pull = fetch(f"https://api.github.com/repos/NixOS/nixpkgs/pulls/{PR}")
    revision = pull["head"]["sha"] if pull["state"] == "open" else fetch("https://api.github.com/repos/NixOS/nixpkgs/commits/nixos-unstable")["sha"]
    previous = shared.published("gnome-cache", "gnome")
    old = previous.get("snapshot", {})
    with ThreadPoolExecutor(max_workers=8) as pool:
        heads = dict(pool.map(lambda n: (n, fetch(api(n, "commits?per_page=1"))[0]["id"]), PROJECTS))
    source_digest = hashlib.sha256(json.dumps(heads, sort_keys=True).encode()).hexdigest()
    changed = previous.get("sourceDigest") != source_digest or previous.get("revision") != revision or previous.get("clientDigest") != digest()
    if changed:
        url = f"https://github.com/NixOS/nixpkgs/archive/{revision}.tar.gz"
        sha256 = old["sha256"] if old.get("revision") == revision else run("nix-prefetch-url", "--unpack", url)
        with ThreadPoolExecutor(max_workers=4) as pool:
            sources = dict(pool.map(lambda n: (n, source(n, heads[n], old.get("sources", {}).get(n, {}))), PROJECTS))
        dump("snapshot.json", {"schema": 1, "mode": "git", "revision": revision, "url": url, "sha256": sha256, "sourceDigest": source_digest, "sources": sources})
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write("build=" + str(changed).lower() + "\n")
    print(f"GNOME Git: {len(heads)} desktop sources; build={changed}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["resolve", "build", "push", "verify", "retain", "publish", "salvage"])
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parent)
    {"resolve": resolve, "build": lambda: lifecycle.build(digest), "push": lifecycle.push, "salvage": lifecycle.salvage, "verify": lambda: lifecycle.verify(digest), "retain": lambda: lifecycle.retain("gnome"), "publish": lambda: shared.publish("gnome-cache")}[args.command]()


if __name__ == "__main__":
    main()
