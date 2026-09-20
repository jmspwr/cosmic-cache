"""Check a candidate against immutable snapshots of the published sibling desktops."""
import argparse
import datetime
import json
import re
from scripts import cache
from scripts.storage import DESKTOPS


def revision(remote, branch):
    result = cache.run("git", "ls-remote", "--heads", remote, "refs/heads/" + branch)
    if not result:
        return None
    sha = result.split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("Invalid publication revision")
    return sha


def check(desktop=None):
    path = cache.ROOT / desktop / "cache-proof.json" if desktop else None
    proof = json.loads(path.read_text()) if path else {}
    try:
        modules = []
        publications = {}
        for name in DESKTOPS:
            if name == desktop:
                modules.append(json.dumps(str(cache.ROOT / name / "default.nix")))
                publications[name] = proof["builderRevision"]
            else:
                sha = revision("origin", name + "-cache")
                if sha is None and desktop is None:
                    raise RuntimeError(f"Missing published {name} desktop")
                if sha is None:
                    continue  # First publication of a new sibling has not happened yet.
                publications[name] = sha
                modules.append(f'(fetchTarball "https://github.com/jmspwr/desktop-cache/archive/{sha}.tar.gz" + "/{name}/default.nix")')
        host = proof.get("referenceSystems", {}).get("nixos-unstable")
        if host is None:
            sha = revision("https://github.com/NixOS/nixpkgs.git", "nixos-unstable")
            if sha is None:
                raise RuntimeError("Missing nixos-unstable branch")
            host = {"revision": sha, "sha256": cache.run("nix-prefetch-url", "--unpack", f"https://github.com/NixOS/nixpkgs/archive/{sha}.tar.gz")}
        host_expr = '(fetchTarball { url = "https://github.com/NixOS/nixpkgs/archive/' + host["revision"] + '.tar.gz"; sha256 = ' + json.dumps(host["sha256"]) + '; })'
        expression = '(import ' + json.dumps(str(cache.ROOT / "checks/combined.nix")) + ') { modules = [ ' + ' '.join(modules) + ' ]; desktops = builtins.fromJSON ' + json.dumps(json.dumps(list(publications))) + '; host = ' + host_expr + '; }'
        result = json.loads(cache.run("nix", "eval", "--impure", "--json", "--expr", expression))
        result = {"candidate": desktop, "publications": publications, "hostRevision": host["revision"], "hostSha256": host["sha256"], "checkedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(), **result}
        if path:
            proof["combinedCheck"] = result
            cache.dump(path, proof)
        else:
            cache.run("nix-build", result["systemDerivation"], "--no-out-link", "--max-jobs", "1", "--cores", "2", *cache.options(), capture=False)
            cache.dump(cache.ROOT / "combined-check.json", result)
        print("Compatible desktop modules:", ", ".join(publications))
    except Exception:
        if path:
            path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("desktop", choices=(*DESKTOPS, "all"))
    desktop = parser.parse_args().desktop
    check(None if desktop == "all" else desktop)


if __name__ == "__main__":
    main()
