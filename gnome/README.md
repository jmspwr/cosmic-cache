# GNOME desktop cache

GNOME's desktop components follow their upstream Git default branches. Everyday applications
are excluded by default: COSMIC supplies the app suite. Import the verified module from
`gnome-cache`, and enable `services.desktopManager.gnome.enable` in your own configuration.

The Git set is GJS, GNOME Shell, Mutter, desktop schemas, session manager, settings daemon,
Control Center and the GNOME portal. Qt/GTK, graphics drivers and other libraries retain the
packaging tree's recipes. A GNOME 51 Nixpkgs integration branch (PR 559510 while open, then
nixos-unstable) supplies dependency versions and NixOS patches. Core sources, pinned submodules
and Meson wraps are resolved and hashed before building. Missing packaging or dependencies
fail the build; there is no silent downgrade from Git.

The consumer passes already-instantiated packages only to the matching GNOME desktop and
settings-daemon modules. It does not overlay the host's package fixpoint. Native GNOME apps,
EasyEffects and COSMIC are unaffected. The separate Extensions control app uses the packaging
tree only when the host is too old to provide it. GNOME core apps are disabled at priority 900;
an explicit `services.gnome.core-apps.enable = true` in your own config can enable native apps.

All core packages build together, so development outputs stay on the runner. Only runtime
outputs (including the session definitions) and a complete public reference system are uploaded.
The profile has no GNOME app bundle and checks that native app identities remain unchanged.
A fresh runner reevaluates the reference and fetches all runtime outputs and its complete closure
with local and remote compilation disabled. After the shared storage budget check, one runtime
snapshot is pinned and `gnome-cache` advances without force-pushing.

The shared workflow serializes COSMIC, Plasma and GNOME updates to avoid overlapping upload
peaks. See the root README for the 5 GiB storage policy and installation instructions. A successful
cache build establishes downloadability and NixOS evaluation, not a graphical-session boot test.
