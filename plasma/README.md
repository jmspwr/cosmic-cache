# Plasma Git cache

Builds current Plasma Git sources for x86_64-linux and publishes verified binaries to
[jmspwr.cachix.org](https://jmspwr.cachix.org). This is the Plasma sibling of
[cosmic-cache](https://github.com/jmspwr/desktop-cache/tree/main/cosmic).

## How it works

1. Every hour, resolve the current Nixpkgs Plasma packaging and each Plasma repository's
   default-branch HEAD on KDE Invent. The open [Plasma packaging PR](https://github.com/NixOS/nixpkgs/pull/561955)
   supplies the recipes; after it closes, use `nixos-unstable`. A manual run can select another
   packaging commit or `beta` mode to use its release tarballs instead.
2. Record component commits and content hashes in `snapshot.json`. Override Nixpkgs'
   `kdePackages.sources` so its dependency scope and NixOS patches stay intact. Qt and Frameworks
   come from the packaging tree. Check the core components' declared minimum versions before building.
3. Discover the packages installed by the representative laptop configuration in `profile.nix`.
   Derive their Plasma dependencies from Nix's actual derivation closures. Divide the graph into
   five waves, grouping dependent packages onto the same runner within a wave. Independent batches
   build in parallel; later waves download all outputs uploaded by earlier waves.
4. On a fresh runner, download **every output of every required Plasma package**, with local and
   remote compilation disabled. Check NixOS assertions and the module's exact selected output paths.
5. Protect those outputs and their runtime closures with a Cachix retention root, keeping two
   revisions. Then advance `plasma-cached` with a normal fast-forward commit containing the source snapshot,
   client code and `cache-proof.json`.

Unchanged component heads, packaging and builder code skip evaluation and builds. Interrupted or
failed runs leave `plasma-cached` unchanged. A new push queues behind a running build instead of cancelling
its uploads. Git failures are reported, not treated as an empty cache. There is no silent fallback
from Git to release sources: choose `beta` explicitly if the development tree needs newer packaging.

The package graph avoids duplicate **Plasma** compilation between batches; unrelated dependencies
can still be built on multiple runners when neither configured cache provides them. Git recipes can
also need new dependencies or adapted patches as upstream evolves. Passing the publication checks
proves substitution and package identity, not that the desktop works on every machine.

## Use

After the first successful publication, add this to your existing NixOS configuration:

```nix
imports = [ "${fetchTarball "https://github.com/jmspwr/desktop-cache/archive/plasma-cached.tar.gz"}/plasma/default.nix" ];
```

Keep `services.desktopManager.plasma6.enable = true` in your configuration. The module supplies a
coherent `kdePackages` scope, checks it against the published proof, and configures the public cache.
It leaves the rest of your system on your own Nixpkgs channel. Custom overlays that replace the
verified Plasma outputs fail an assertion.

For the **first** rebuild, give the running Nix daemon the cache settings explicitly; the module's
settings only take effect after activation:

```sh
sudo nixos-rebuild switch --impure \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0
```

`plasma-cached` is a rolling channel of completed builds. Recorded revisions make each publication
reproducible; they do not require you to manage pins. Nix caches mutable tarball URLs, so a rebuild
may reuse a recently fetched channel until its tarball TTL expires.

Only standard public GitHub runners are used. The Cachix write token is available only to upload
and retention steps. Pull requests run regression and syntax checks without cache credentials.
No personal NixOS system, configuration or proprietary applications are uploaded.

## Checks

```sh
python3 -m unittest discover -s tests -v # from the repository root
for file in *.nix cosmic/*.nix plasma/*.nix; do nix-instantiate --parse "$file" > /dev/null; done
actionlint
```
