# Desktop cache

Rolling, verified **COSMIC and KDE Plasma Git builds** for x86_64-linux, published to
[jmspwr.cachix.org](https://jmspwr.cachix.org).

| Desktop | Sources | Verified branch | Module |
| --- | --- | --- | --- |
| COSMIC | Component Git HEADs through `amozeo/nixos-cosmic` | `cosmic-cache` | `cosmic/default.nix` |
| Plasma | Component Git HEADs on KDE Invent, using Nixpkgs recipes | `plasma-cache` | `plasma/default.nix` |

Each workflow polls hourly and builds only changed snapshots. It advances its verified branch
only after a fresh runner downloads the promised outputs with compilation disabled. A NixOS
evaluation checks the module's assertions and exact package paths. Plasma also builds complete
public reference systems, including Gear, Qt5 integration and EasyEffects, and fetches their entire
closures on a fresh runner without compilation. Cachix retention protects the
latest publication for each desktop. A failure in one desktop does not hold back the other.

## Install

Merge the imports for the desktops you use into your existing configuration:

```nix
imports = [
  "${builtins.fetchTarball "https://github.com/jmspwr/desktop-cache/archive/cosmic-cache.tar.gz"}/cosmic/default.nix"
  "${builtins.fetchTarball "https://github.com/jmspwr/desktop-cache/archive/plasma-cache.tar.gz"}/plasma/default.nix"
];
nix.settings.experimental-features = [ "nix-command" "flakes" ];
services.desktopManager.cosmic.enable = true;
services.desktopManager.plasma6.enable = true;
```

Preserve your other imports and settings, and keep one display manager enabled for both sessions.
Each import requires its desktop's first successful publication.

Keep your desktop's `services.desktopManager` declaration in your own configuration. The modules
supply the verified packages and public cache settings. Root `default.nix` and `packages.nix`
remain COSMIC compatibility entry points. Update older COSMIC URLs from `cached` to `cosmic-cache`.

For the first rebuild, make the cache available to the current Nix daemon explicitly:

```sh
sudo nixos-rebuild switch --impure \
  --option extra-experimental-features 'nix-command flakes' \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0 \
  --option tarball-ttl 0
```

After activation, the module supplies these settings. Each desktop uses its recorded dependency
set alongside your system's own Nixpkgs. Local system assembly still happens normally; the cache
guarantee applies to the verified desktop outputs, not every package on your machine. Nix may reuse
a recently fetched channel tarball until its TTL expires; use `--option tarball-ttl 0`
when rebuilding to check for a newer publication. Preserve your normal `--flake` selection if
your configuration uses one. COSMIC requires flake support internally even for a conventional
`configuration.nix`.

## Build design

- [`cosmic/`](cosmic): follows all tracked component heads using upstream's packaging updater,
  builds independent applications on separate runners, and retains their runtime closures.
- [`plasma/`](plasma): resolves exact KDE Invent commits and hashes, overrides the complete KDE
  package scope's sources, and groups actual Plasma dependencies into five parallel build waves.
  The consumer imports the matching Plasma NixOS module alongside those packages, avoiding
  obsolete package references in the host's Plasma module. Git packages are passed only to that
  module: the host's `pkgs.kdePackages`, Gear apps, Qt5 variants and EasyEffects keep their channel
  identities. Enabling this cache does not redirect unrelated applications to Git Breeze.
  Every non-debug output of every required Plasma package is uploaded, verified and retained,
  including headers and session files. Separate debug symbols and their source trees are not
  explicitly uploaded. Manual `beta` mode uses the packaging tree's release tarballs.
- [`scripts/cache.py`](scripts/cache.py): shared cache configuration, digest, transport and
  fast-forward publication. Network errors never masquerade as an unpublished cache.

New pushes queue behind active builds so they cannot cancel uploads or retention midway through.
Published snapshots record exact commits for reproducibility while the channels keep rolling.
Git source changes can require updated packaging or patches; failed builds preserve the previous
publication. No failed Git build silently publishes a beta instead.

New uploads use XZ level 6 to favor storage density over compression speed. Cachix does not
recompress already-present paths, and paths available in the official NixOS cache are skipped.
To fit a small Cachix quota, retention keeps one successful revision per desktop. This does not
remove local NixOS generations. Older remote binaries become eligible for garbage collection;
they are not guaranteed for a fresh rollback download. Uploading the next revision still needs
headroom alongside the current one. Previously uploaded debug outputs or old beta builds are not
deleted by changing the output selection; Cachix must reclaim eligible unpinned data. Debug
symbols can still be built locally when needed, using the unchanged package derivations.

Only standard public GitHub runners are used. Desktop compilation has no Cachix write token;
only upload and retention steps receive it. Pull requests run checks without cache credentials.
Plasma's complete-system fixtures use only the public profile in this repository. No personal
NixOS configurations, proprietary apps or secrets are uploaded.

If a Plasma run is interrupted, manually dispatch its workflow with `resume_run` set to the
previous run ID. It downloads that run's snapshot artifact and preserves its exact source
commits/hashes while using the current builder and output policy. Leave `resume_run` empty
for normal rolling updates. Resume requires the original artifact to remain available.

## Development

```sh
python3 -m unittest discover -s tests -v
for file in *.nix cosmic/*.nix plasma/*.nix; do nix-instantiate --parse "$file" > /dev/null; done
actionlint
```

Run builders from the repository root with `python3 -m cosmic.ci` or `python3 -m plasma.ci`.
The generated snapshot and verification files belong to the publication branches, not `main`.
