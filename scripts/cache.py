"""Shared cache transport and atomic publication for the desktop builders."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# Spend runner CPU on compression instead of scarce persistent cache storage.
PUSH_OPTIONS = ("--compression-method", "xz", "--compression-level", "6")


def run(*args: str, capture: bool = True, cwd: str | Path | None = None,
        env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args, check=True, text=True, env=env, cwd=cwd,
        timeout=120 if args[:2] == ("git", "ls-remote") else None,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def dump(path: str | Path, value: object) -> None:
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def cache() -> dict:
    value = json.loads((ROOT / "cache.json").read_text())
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


def client_digest(files: list[str]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.encode() + b"\0" + (ROOT / path).read_bytes() + b"\0")
    return digest.hexdigest()


def published(branch: str, desktop: str) -> dict:
    if not run("git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"):
        return {}
    run("git", "fetch", "--no-tags", "--depth", "1", "origin", f"refs/heads/{branch}", capture=False)
    files = run("git", "ls-tree", "--full-tree", "-r", "--name-only", "FETCH_HEAD").splitlines()
    # Existing COSMIC publications predate the desktop subdirectories.
    prefix = f"{desktop}/" if f"{desktop}/cache-proof.json" in files else ""
    proof = json.loads(run("git", "show", "FETCH_HEAD:" + prefix + "cache-proof.json"))
    proof["snapshot"] = json.loads(run("git", "show", "FETCH_HEAD:" + prefix + "snapshot.json"))
    return proof


def publish(branch: str) -> None:
    for path in ("snapshot.json", "cache-proof.json"):
        if not Path(path).is_file():
            raise RuntimeError(f"Missing publication evidence: {path}")
    ref = f"refs/heads/{branch}"
    parent = run("git", "rev-parse", "HEAD")
    if run("git", "ls-remote", "--heads", "origin", ref):
        run("git", "fetch", "--no-tags", "origin", ref, capture=False)
        parent = run("git", "rev-parse", "FETCH_HEAD")
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "--force", "snapshot.json", "cache-proof.json")
    tree = run("git", "write-tree")
    commit = run("git", "commit-tree", tree, "-p", parent, "-m", f"Publish verified {branch} snapshot")
    run("git", "push", "origin", f"{commit}:{ref}", capture=False)
    print(f"Published {branch}: {commit}")
