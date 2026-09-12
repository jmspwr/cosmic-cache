# COSMIC binary cache builder

Public x86_64 COSMIC Git cache builder for `jmspwr`.

This is a dedicated public builder repository, not a copy of a personal NixOS configuration.
It follows COSMIC component HEADs through the packaging/update machinery in `amozeo/nixos-cosmic`.

## Architecture

GitHub Actions resolves one source snapshot, builds the x86_64 COSMIC desktop packages on separate
standard Linux runners, and uploads their runtime closures to the public `jmspwr` Cachix cache. It does
not upload an entire NixOS system, personal configuration, proprietary apps, authentication files or
build secrets. The per-cache Cachix write token is available only to upload/retention steps, not desktop
compilation. There are no pull-request-triggered privileged builds. The workflow polls component HEADs
hourly and rebuilds only when a component moved or the client definition (`default.nix`, `packages.nix`,
the workflow, `scripts/ci.py`) changed; the `cached` branch is bound to the exact client definition that
was verified.

A fresh final runner must obtain every selected output with local compilation disabled and no remote
builders. The primary COSMIC derivations must not set `preferLocalBuild`. A NixOS module evaluation then
checks that the module selects identical output paths. Only after these checks and Cachix retention
succeed is the `cached` branch advanced. This verifies substitution at that moment, not GUI correctness
on a particular laptop or permanent future availability of the provider.

The module imports matching NixOS integration modules from the source snapshot and supplies its
already-instantiated package outputs. It does not rebuild that package set against the user's channel.
This adds a separate Nixpkgs dependency set for COSMIC, not a replacement for the whole system's channel.
The existing `services.desktopManager.cosmic.enable` and `services.displayManager.cosmic-greeter.enable`
declarations remain in the user's configuration.

## Activation

Add this to the existing imports only after the `cached` branch has a successful publication:

```nix
"${fetchTarball "https://github.com/jmspwr/cosmic-cache/archive/cached.tar.gz"}/default.nix"
```

The module persistently configures `https://jmspwr.cachix.org` and its public signing key for subsequent
Nix invocations. There is one bootstrap detail: settings produced by a NixOS configuration do not become
the running nix-daemon configuration until that configuration has been activated. Therefore the first
preflight/rebuild must provide the Cachix URL and key to the current Nix process explicitly.

First, strictly prove that every selected COSMIC output can be substituted, with all local and remote
builders disabled:

```sh
sudo nix-build --expr '
let
  c = fetchTarball "https://github.com/jmspwr/cosmic-cache/archive/cached.tar.gz";
in builtins.map (p: p.out) (builtins.attrValues (import (c + "/packages.nix")))
' \
  --no-out-link \
  --max-jobs 0 \
  --option builders "" \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0 \
  --option fallback false
```

A successful command means the evaluated COSMIC package outputs required no compilation. If it reports
`Cannot build` for a COSMIC derivation, abort activation and fix the cache rather than enabling builders.

Then perform the first system rebuild with the same bootstrap cache settings, but do **not** set
`max-jobs = 0` for the complete NixOS build. NixOS must still create ordinary machine-specific system
assembly derivations locally:

```sh
sudo nixos-rebuild switch --impure \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0
```

After that switch, the module's persistent `nix.settings` makes the `jmspwr` cache available normally.
Do not enable the source-only `amozeo/nixos-cosmic` import as well.

The `cached` branch rolls only after completed cache verification. `snapshot.json` records the exact
source revision that was built; the matching dependency lock is retained. This is build provenance, not
a user-managed freeze of the moving cached channel.

## Known upstream workaround

`cosmic-comp` depends on the `libdisplay-info-sys` 0.3 crate, which binds the 0.3 C API, while
`amozeo/nixos-cosmic` builds it against Nixpkgs' default `libdisplay-info` (0.4.0 at the time of writing),
so upstream's own build fails. `packages.nix` overrides `cosmic-comp` with `libdisplay-info_0_3` — the same
choice Nixpkgs' own `cosmic-comp` recipe makes — for as long as the upstream recipe takes a `libdisplay-info`
argument. The override switches itself off when upstream changes that argument; the proper fix is upstream.

## Resource and spending limits

Only standard `ubuntu-24.04` GitHub-hosted runners are selected, and the workflow is gated to public
repositories. No paid runner, subscription, trial or billing change is created.

Only runtime closures are pushed. A named Cachix retention root protects completed snapshots. Older
remote cache entries may become eligible for Cachix's own storage management. This does not delete local
files, NixOS generations or local Nix store entries. No local garbage-collection, pruning or deletion
commands are included.

## Security

The Cachix write token is stored only as a GitHub Actions secret. It must never be committed, pasted into
issues, logs or chat, or placed in a NixOS configuration. Client machines need only the public cache URL
and public signing key above.

## Primary references

- https://docs.cachix.org/getting-started
- https://docs.cachix.org/continuous-integration-setup/github-actions
- https://docs.cachix.org/pushing
- https://docs.cachix.org/pins
- https://nix.dev/manual/nix/stable/command-ref/conf-file
- https://github.com/amozeo/nixos-cosmic
