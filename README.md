# COSMIC cache

Rolling upstream Git builds of **COSMIC and its application suite** for x86_64-linux,
published to [jmspwr.cachix.org](https://jmspwr.cachix.org).

## Use

Merge into your existing `configuration.nix`:

```nix
imports = [
  "${builtins.fetchTarball "https://github.com/jmspwr/cosmic-cache/archive/cosmic-cache.tar.gz"}/default.nix"
];
services.desktopManager.cosmic.enable = true;
services.displayManager.cosmic-greeter.enable = true;
```

Preserve your hardware configuration, other imports and system settings. Keep one display manager;
omit the greeter line if you already use another. Remove any competing source-only COSMIC import.
The module adds the cache URL, public signing key and required Nix experimental features.
No Cachix account or write token is needed on the consuming machine.

For the first build, supply those settings to the running Nix daemon explicitly:

```sh
sudo nixos-rebuild dry-build --impure \
  --option extra-experimental-features 'nix-command flakes' \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0 \
  --option tarball-ttl 0
```

Inspect the result, repeat with `build`, then use `switch` to activate it. Preserve your usual
`--flake /path#host` selection if applicable. Afterwards, refresh with
`sudo nixos-rebuild switch --impure --option tarball-ttl 0`.

The publication branch rolls automatically; there are no user-managed version pins. A source commit
becomes available only after its build and verification succeed. Machine-specific system assembly
and unrelated packages can still need local builds. Never disable all builders for a complete personal
system rebuild. Updating this cache does not update your own Nixpkgs channel or activate your machine.

## How it works

1. Poll upstream packaging and component HEADs hourly, on `main` pushes, or by manual dispatch.
2. Run `amozeo/nixos-cosmic`'s updater and require every tracked component to match its resolved HEAD.
   Save immutable recipes, dependency locks and source hashes on the `source` branch.
3. Build the desktop and apps on separate standard GitHub runners. Upload runtime closures only;
   successful outputs survive another component's failure.
4. Build a complete public NixOS reference system with COSMIC, its greeter, networking and audio.
   Check exact package identities, session registration and preservation of the host's ordinary apps.
5. On a fresh runner, fetch every promised output and the complete reference closure with local and
   remote compilation disabled. Reject mismatched source, builder, client or reference evidence.
6. Measure compressed cache use and protect both the new candidate and the currently advertised
   snapshot. Advance `cosmic-cache` without force-pushing, then release the previous retention.

Unchanged verified sources, reference channel and client definitions skip package rebuilding. Active builds finish before
a later update starts. Failures leave the previous publication in place. Retention always follows the
actually published snapshot, including after repeated failed attempts; a branch race stops publication.

The consumer imports matching upstream NixOS integration and already-instantiated COSMIC packages.
Ordinary applications retain their host channel's package definitions. Assertions reject an incompatible
architecture, stale proof, or competing overlay that changes a cached COSMIC output.

`main` contains the builder. `source` contains immutable upstream packaging snapshots without upstream
workflows. `cosmic-cache` contains only consumer files, documentation and verification evidence: `cosmic/snapshot.json` and
`cosmic/cache-proof.json`. Build workflows are not shipped in that branch. Import the publication branch, never `main` or `source`.

## Storage and credentials

Official NixOS cache dependencies are reused. Uploads use XZ compression; separate debug outputs and
build-only dependencies are not retention roots. One COSMIC runtime snapshot and its public reference
system remain protected after publication. Before changing retention, CI requires the current runtime
closure to fit within **4 GiB**, and the union with the outgoing snapshot within **4.75 GiB**.

The storage report counts compressed custom-cache paths once. It is not the account's total usage:
old unpinned uploads may remain until [Cachix garbage collection](https://docs.cachix.org/garbage-collection)
reclaims them. [Retention pins](https://docs.cachix.org/pins) protect the advertised runtime. Personal
NixOS configurations and local rollback generations are never uploaded or deleted.

The source updater runs without publication credentials. Compilation receives no Cachix write token.
Only upload/retention steps receive the cache-scoped secret; only isolated publication jobs receive
GitHub write credentials. Pull requests run unprivileged checks and cannot publish.

Successful build, substitution and integration checks establish the recorded reference result. They
cannot guarantee graphical behavior on every machine or prevent upstream Git regressions. A failed
upstream update is reported rather than silently falling back to an older source under a new label.

## Development

```sh
python3 -m unittest discover -s tests -v
for file in *.nix cosmic/*.nix; do nix-instantiate --parse "$file" > /dev/null; done
actionlint
```

`cosmic/ci.py` owns the lifecycle; `cosmic/packages.nix` selects the desktop and app suite;
`cosmic/default.nix` is the consumer module; `cosmic/profile.nix` and `cosmic/check.nix` define the public
reference check. `scripts/cache.py` handles transport/publication and `scripts/storage.py` measures the
runtime footprint. Root Nix files are short consumer entry points.
