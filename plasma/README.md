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
   build in parallel; later waves download non-debug outputs uploaded by earlier waves.
4. Build complete public reference systems on current `nixos-unstable` and the host revision from
   the EasyEffects regression. These exclude optional Gear apps and include Qt5 integration and EasyEffects.
   Assert that application store paths match the unmodified host package set, and upload complete
   reference runtime closures. Compilation runs with one build job and two cores, without cache credentials.
5. On a fresh runner, download **every runtime output of every required Plasma package**, including session definitions, and both
   complete reference closures with local and remote compilation disabled. Independently evaluate
   their full systems and application identities, and also evaluate the packaging-tree host.
6. Protect those outputs and the reference closures with a Cachix retention root, keeping one
   revision, after checking the combined desktop storage budget. Then advance `plasma-cache` with a normal fast-forward commit containing the source snapshot,
   client code and `cache-proof.json`.

Unchanged component heads, packaging and builder code skip evaluation and builds. Interrupted or
failed runs leave `plasma-cache` unchanged. A new push queues behind a running build instead of cancelling
its uploads. Git failures are reported, not treated as an empty cache. There is no silent fallback
from Git to release sources: choose `beta` explicitly if the development tree needs newer packaging.

The package graph avoids duplicate **Plasma** compilation between batches; unrelated dependencies
can still be built on multiple runners when neither configured cache provides them. Git recipes can
also need new dependencies or adapted patches as upstream evolves. Passing the publication checks
proves substitution and package identity, not that the desktop works on every machine.

Separate `debug` outputs are intentionally omitted from uploads, verification and retention.
They contain debugging symbols and reference source trees; neither is required to run Plasma.
Package recipes, source commits and output paths are unchanged, so existing non-debug binaries
remain reusable. Headers and build tools can be uploaded for later CI waves, but are no longer pinned; runtime outputs and session files remain protected. This is an output
selection policy, not a `separateDebugInfo` override that would force a rebuild of the desktop.
If a required output genuinely references a debug path, its closure still includes that path.

Only the latest successful revision is protected. A new upload needs headroom alongside it;
old unpinned builds are eligible for Cachix garbage collection. Changing this policy does not
immediately delete already-uploaded data. Local NixOS generations are unaffected.

## Use

After the first successful publication, add this to your existing NixOS configuration:

```nix
imports = [ "${fetchTarball "https://github.com/jmspwr/desktop-cache/archive/plasma-cache.tar.gz"}/plasma/default.nix" ];
```

Keep `services.desktopManager.plasma6.enable = true` in your configuration. The module passes the
cached Git components directly to its matching Plasma NixOS module, checks the packages against the
published proof, and configures the public cache. It replaces the host's Plasma module so older
package lists cannot request removed components such as `kwin-x11` or `kgamma`.
It does **not** overlay the host's `pkgs.kdePackages`. Gear applications, EasyEffects and the Qt5
Breeze/integration variants keep their ordinary channel derivations, rather than rebuilding against
Git Breeze. Optional application bundles are excluded by default using `plasma/minimal.nix`; ordinary user declarations can override the exclusion list. The public profile checks that excluded applications stay absent and native application identities remain unchanged.
Conflicting explicitly installed Plasma components fail an assertion. Additional personal apps
still follow your channel's cache availability, and your own system assembly still runs locally.

For the **first** rebuild, give the running Nix daemon the cache settings explicitly; the module's
settings only take effect after activation:

```sh
sudo nixos-rebuild switch --impure \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0
```

`plasma-cache` is a rolling channel of completed builds. Recorded revisions make each publication
reproducible; they do not require you to manage pins. Nix caches mutable tarball URLs, so a rebuild
may reuse a recently fetched channel until its tarball TTL expires.

Only standard public GitHub runners are used. The Cachix write token is available only to upload
and retention steps. Pull requests run regression and syntax checks without cache credentials.
Only the repository's public reference systems are uploaded; no personal NixOS configuration,
system or proprietary applications are uploaded.

## Checks

```sh
python3 -m unittest discover -s tests -v # from the repository root
for file in *.nix cosmic/*.nix plasma/*.nix gnome/*.nix; do nix-instantiate --parse "$file" > /dev/null; done
actionlint
```
