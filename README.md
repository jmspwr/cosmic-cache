# Desktop cache

Rolling, verified **COSMIC, Plasma, GNOME and LXQt Git desktops** for x86_64-linux, published to
[jmspwr.cachix.org](https://jmspwr.cachix.org).

| Desktop | Git scope | Verified branch | Module |
| --- | --- | --- | --- |
| COSMIC | Desktop and its application suite | `cosmic-cache` | `cosmic/default.nix` |
| Plasma | Desktop, settings and integration; optional application bundle excluded | `plasma-cache` | `plasma/default.nix` |
| GNOME | Shell, Mutter, session, settings, schemas, GJS and portal; core apps disabled | `gnome-cache` | `gnome/default.nix` |
| LXQt | Desktop, settings, libraries and portal; optional apps excluded | `lxqt-cache` | `lxqt/default.nix` |

Plasma, GNOME and LXQt use private package arguments for their NixOS modules. They do not replace the
host's KDE/GNOME/LXQt package scopes, so ordinary applications retain their channel derivations.
COSMIC retains its desktop and app suite. Desktop imports do not enable sessions themselves.

## Install

Merge the imports for the desktops you want into your existing configuration:

```nix
imports = [
  "${builtins.fetchTarball "https://github.com/jmspwr/desktop-cache/archive/cosmic-cache.tar.gz"}/cosmic/default.nix"
  "${builtins.fetchTarball "https://github.com/jmspwr/desktop-cache/archive/plasma-cache.tar.gz"}/plasma/default.nix"
  "${builtins.fetchTarball "https://github.com/jmspwr/desktop-cache/archive/gnome-cache.tar.gz"}/gnome/default.nix"
  "${builtins.fetchTarball "https://github.com/jmspwr/desktop-cache/archive/lxqt-cache.tar.gz"}/lxqt/default.nix"
];
nix.settings.experimental-features = [ "nix-command" "flakes" ];
services.desktopManager = {
  cosmic.enable = true;
  gnome.enable = true;
  plasma6.enable = true;
};
services.xserver.desktopManager.lxqt.enable = true;
```

LXQt includes its Wayland session with channel Labwc and swaylock. On first login, choose Labwc
in LXQt Session Settings. PCManFM-Qt remains because it draws the desktop and icons.
Optional terminal, image viewer, archive manager and other bundled apps are excluded.

Preserve your hardware, users, other imports and existing display manager. Use one display manager
for the available sessions. Each publication branch becomes usable only after its first successful
build; `main` intentionally lacks the generated snapshot and verification files. Each desktop must
come from its own publication branch.

The modules add the cache URL and public signing key. No Cachix write token is needed on your
machine. Supply the settings explicitly before they have been activated, and inspect a dry build:

```sh
sudo nixos-rebuild dry-build --impure \
  --option extra-experimental-features 'nix-command flakes' \
  --option extra-substituters https://jmspwr.cachix.org \
  --option extra-trusted-public-keys 'jmspwr.cachix.org-1:Ta+OFK/CrEpoz6PfkAuz2le3tZoTyFKshQpTwm5iccw=' \
  --option narinfo-cache-negative-ttl 0 \
  --option tarball-ttl 0
```

Use `build` to finish without activating, then `switch` when ready. Preserve your normal `--flake`
selection if applicable. COSMIC requires flake support internally even with a conventional
`configuration.nix`. Refreshing a moving tarball adopts the latest successful publication; CI does
not automatically update an installed machine. Native applications and local system assembly
remain governed by the host configuration and channel.

## Storage policy

The cache is designed for a shared **5 GiB** allowance:

- Reuse official NixOS cache paths; Cachix skips uploading those dependencies.
- Upload with XZ level 6 and retain only one runtime publication per desktop.
- Exclude Plasma/GNOME/LXQt app bundles and separate debug symbols from the promised runtime set.
- Keep GNOME/LXQt build helpers on its runner. Plasma's multi-runner build may upload non-debug
  development outputs for later waves, but its retention root protects runtime outputs and
  complete reference systems only. Unneeded build helpers become eligible for garbage collection.
- Serialize all desktop pipelines through one hourly workflow, preserving completed uploads.
- Before retention/publication, measure compressed sizes through Nix's binary-cache metadata.
  Shared store paths count once and official-cache paths cost zero. Refuse publication above
  4 GiB of combined current runtimes, or 4.75 GiB including the outgoing desktop snapshot.

`storage-report.json` and each newly published proof report the measured runtime budget. This is
not total account usage: old unpinned generations, previous debug uploads and unrelated pins can
still occupy space. Cachix garbage-collects eligible older paths as the account reaches its limit;
new retention settings do not instantly delete or recompress existing uploads. Local NixOS
rollback generations are unaffected. See [Cachix garbage collection](https://docs.cachix.org/garbage-collection)
and [pin retention](https://docs.cachix.org/pins).

## Build and verification

The shared workflow polls hourly, runs on `main` pushes, and supports selecting one desktop.
COSMIC uses `amozeo/nixos-cosmic`'s updater and verifies component HEADs. Plasma resolves KDE
Invent HEADs with Nixpkgs recipes (PR 561955 while open); GNOME resolves GNOME GitLab HEADs
with its integration packaging. LXQt resolves each desktop repository’s default-branch HEAD
against nixos-unstable packaging. Sources and hashes are immutable within each build. Unchanged
source/client snapshots skip rebuilding. Completed GNOME/LXQt runtime outputs are salvaged after build failures. A failed desktop does not stop the other desktop jobs,
but it leaves its own previous publication in place. Plasma's explicit `beta` mode is available
through manual dispatch; Git failures never silently fall back to it.

Fresh verification runners fetch promised runtime outputs with local and remote compilation
disabled. Plasma, GNOME and LXQt also build and fetch complete public reference systems and compare
native application identities with an unmodified host. The shared workflow also evaluates all four published modules together. Their consumer modules check exact cached
package identities. Successful evaluation/build/download checks do not establish graphical boot
or arbitrary old-channel compatibility.

Only public fixture systems are uploaded, never personal configurations or secrets. Compilation
has no Cachix write token; upload and retention steps receive it separately. Publication uses a
normal fast-forward update after verification and retention. For an interrupted Plasma build,
dispatch the shared workflow with `desktop=plasma` and its old run ID in `resume_run` while the
snapshot artifact remains available.

## Development

```sh
python3 -m unittest discover -s tests -v
for file in *.nix cosmic/*.nix plasma/*.nix gnome/*.nix lxqt/*.nix checks/*.nix; do nix-instantiate --parse "$file" > /dev/null; done
actionlint
```

Run desktop commands from the repository root with `python3 -m cosmic.ci`, `python3 -m plasma.ci`
`python3 -m gnome.ci` or `python3 -m lxqt.ci`. `scripts/cache.py` owns shared publication/transport settings;
`scripts/desktop.py` shares GNOME/LXQt lifecycle checks; `scripts/storage.py` measures the shared runtime union. Root `default.nix` and `packages.nix`
remain COSMIC compatibility entry points.
