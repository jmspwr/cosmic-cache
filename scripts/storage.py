"""Measure the shared compressed runtime footprint; never guess from NAR sizes."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

from scripts.cache import ROOT, cache, dump

DESKTOPS = ("cosmic", "plasma", "gnome", "lxqt")
GIB = 1024 ** 3


def get(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read().decode()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def roots(proof: dict) -> set[str]:
    return set(proof.get("runtimePaths", [p["path"] for p in proof["packages"].values()])) | {
        s["systemPath"] for s in proof.get("referenceSystems", {}).values()
    }


def published() -> dict[str, set[str]]:
    result = {}
    for desktop in DESKTOPS:
        data = get(f"https://raw.githubusercontent.com/jmspwr/desktop-cache/{desktop}-cache/{desktop}/cache-proof.json")
        if data is not None:
            result[desktop] = roots(json.loads(data))
    return result



def inventory(groups: dict[str, set[str]]) -> dict:
    uri = cache()["uri"]
    entries = {}
    pending = set().union(*groups.values()) if groups else set()

    def remote(uri, path):
        result = subprocess.run(
            ["nix", "path-info", "--store", uri, "--json", path,
             "--option", "narinfo-cache-negative-ttl", "0"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90,
        )
        if result.returncode:
            if "is not valid" in result.stderr and "HTTP error" not in result.stderr:
                return None
            raise RuntimeError(result.stderr)
        return json.loads(result.stdout)[path]

    def inspect(path):
        if not re.fullmatch(r"/nix/store/[0-9a-z]{32}-[^/\s]+", path):
            raise ValueError(f"Invalid store path: {path}")
        if remote("https://cache.nixos.org", path) is not None:
            return path, {"bytes": 0, "references": set()}
        data = remote(uri, path)
        if data is None:
            raise RuntimeError(f"Runtime output missing from both caches: {path}")
        return path, {"bytes": data["downloadSize"], "references": set(data["references"])}

    with ThreadPoolExecutor(max_workers=16) as pool:
        while pending:
            found = dict(pool.map(inspect, sorted(pending)))
            entries.update(found)
            pending = set().union(*(p["references"] for p in found.values())) - entries.keys()

    closures = {}
    for name, paths in groups.items():
        seen = set()
        pending = set(paths)
        while pending:
            path = pending.pop()
            if path in seen:
                continue
            seen.add(path)
            pending.update(entries[path]["references"] - seen)
        closures[name] = seen
    charged = {p: e["bytes"] for p, e in entries.items() if e["bytes"]}
    return {
        "schema": 1,
        "method": "Cachix narinfo FileSize; official-cache paths excluded; shared paths counted once",
        "compressedBytes": sum(charged.values()),
        "paths": charged,
        "desktops": {n: {"compressedBytes": sum(entries[p]["bytes"] for p in c), "cachePaths": sum(entries[p]["bytes"] > 0 for p in c)} for n, c in closures.items()},
    }


def check(desktop: str | None = None) -> dict:
    groups = published()
    previous = groups.get(desktop, set())
    if desktop:
        groups[desktop] = roots(json.loads((ROOT / desktop / "cache-proof.json").read_text()))
    report = inventory(groups)
    report["runtimeBudgetBytes"] = 4 * GIB
    if report["compressedBytes"] > report["runtimeBudgetBytes"]:
        raise RuntimeError("Current desktop runtime union exceeds the 4 GiB budget; refuse publication")
    if desktop and previous:
        overlap = inventory({**groups, "previous-" + desktop: previous})
        report["updateOverlapBytes"] = overlap["compressedBytes"]
        if overlap["compressedBytes"] > 4.75 * GIB:
            raise RuntimeError("Old and new runtime snapshots exceed the update headroom budget")
    report["scope"] = "Published runtime closures, not total account usage or obsolete unpinned data"
    dump(ROOT / "storage-report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "paths"}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--desktop", choices=DESKTOPS)
    check(parser.parse_args().desktop)
