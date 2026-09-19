# Desktop cache

Rolling, verified **COSMIC and KDE Plasma Git builds** for x86_64-linux, published to
[jmspwr.cachix.org](https://jmspwr.cachix.org).

| Desktop | Sources | Verified branch | Module |
| --- | --- | --- | --- |
| COSMIC | Component Git HEADs through `amozeo/nixos-cosmic` | `cached` | `cosmic/default.nix` |
| Plasma | Component Git HEADs on KDE Invent, using Nixpkgs recipes | `plasma-cached` | `plasma/default.nix` |

Each workflow polls hourly, builds only changed snapshots, and advances its own verified branch
only after a fresh runner downloads the promised outputs with compilation disabled. A NixOS
evaluation checks the module's assertions and exact package paths. Cachix retention protects the
latest two publications for each desktop. A failure in one desktop does not hold back the other.

## Install

Use the module for your desktop after its first successful publication:

```nix
# COSMIC
imports = [ "${fetchTarball "https://github.com/jmspwr/desktop-cache/archive/cached.tar.gz"}/cosmic/default.nix" ];
```

```nix
# Plasma
imports = [ "${fetchTarball "https://github.com/jmspwr/desktop-cache/archive/plasma-cached.tar.gz"}/plasma/default.nix" ];
```

Keep your desktop's `services.desktopManager` declaration in your own configuration. The modules
supply the verified packages and public cache settings. Root `default.nix` and `packages.nix`
remain COSMIC compatibility entry points; existing COSMIC imports keep working across the rename.

For the first rebuild, make the cache available to the current Nix daemon explicitly:

```sh
sudo nixos-rebuild switch --impure \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0
```

After activation, the module supplies these settings. Each desktop uses its recorded dependency
set alongside your system's own Nixpkgs. Local system assembly still happens normally; the cache
guarantee applies to the verified desktop outputs, not every package on your machine. Nix may reuse
a recently fetched channel tarball until its TTL expires.

## Build design

- [`cosmic/`](cosmic): follows all tracked component heads using upstream's packaging updater,
  builds independent applications on separate runners, and retains their runtime closures.
- [`plasma/`](plasma): resolves exact KDE Invent commits and hashes, overrides the complete KDE
  package scope's sources, and groups actual Plasma dependencies into five parallel build waves.
  Every output of every required Plasma package is uploaded, verified and retained, including
  headers and session files. Manual `beta` mode uses the packaging tree's release tarballs.
- [`scripts/cache.py`](scripts/cache.py): shared cache configuration, digest, transport and
  fast-forward publication. Network errors never masquerade as an unpublished cache.

New pushes queue behind active builds so they cannot cancel uploads or retention midway through.
Published snapshots record exact commits for reproducibility while the channels keep rolling.
Git source changes can require updated packaging or patches; failed builds preserve the previous
publication. No failed Git build silently publishes a beta instead.

Only standard public GitHub runners are used. Desktop compilation has no Cachix write token;
only upload and retention steps receive it. Pull requests run checks without cache credentials.
No personal NixOS configurations, whole systems, proprietary apps or secrets are uploaded.

## Development

```sh
python3 -m unittest discover -s tests -v
for file in *.nix cosmic/*.nix plasma/*.nix; do nix-instantiate --parse "$file" > /dev/null; done
actionlint
```

Run builders from the repository root with `python3 -m cosmic.ci` or `python3 -m plasma.ci`.
The generated snapshot and verification files belong to the publication branches, not `main`.
