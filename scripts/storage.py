"""Measure the shared compressed runtime footprint; never guess from NAR sizes."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess

from scripts.cache import ROOT, cache, dump, published as published_proof

GIB = 1024 ** 3


def roots(proof: dict) -> set[str]:
    return set(proof.get("runtimePaths", [p["path"] for p in proof["packages"].values()])) | {
        s["systemPath"] for s in proof.get("referenceSystems", {}).values()
    }


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
        "snapshots": {n: {"compressedBytes": sum(entries[p]["bytes"] for p in c), "cachePaths": sum(entries[p]["bytes"] > 0 for p in c)} for n, c in closures.items()},
    }


def check(candidate: bool = False, published: dict | None = None) -> dict:
    if published is None:
        published = published_proof("cosmic-cache", "cosmic")
    previous = roots(published) if published else set()
    current = roots(json.loads((ROOT / "cosmic/cache-proof.json").read_text())) if candidate else previous
    if not current:
        raise RuntimeError("No COSMIC runtime publication to measure")
    report = inventory({"current": current})
    report["runtimeBudgetBytes"] = 4 * GIB
    if report["compressedBytes"] > report["runtimeBudgetBytes"]:
        raise RuntimeError("COSMIC runtime exceeds the 4 GiB budget; refuse publication")
    if candidate and previous:
        overlap = inventory({"current": current, "previous": previous})
        report["updateOverlapBytes"] = overlap["compressedBytes"]
        if overlap["compressedBytes"] > 4.75 * GIB:
            raise RuntimeError("Old and new runtime snapshots exceed the update headroom budget")
    report["scope"] = "COSMIC runtime closures, not total account usage or obsolete unpinned data"
    dump(ROOT / "storage-report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "paths"}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="store_true")
    check(parser.parse_args().candidate)
