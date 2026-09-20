# LXQt Git cache

Import `lxqt/default.nix` from the verified `lxqt-cache` branch and enable
`services.xserver.desktopManager.lxqt.enable = true;`. The module adds a Wayland
session to your existing display manager, channel Labwc, swaylock and the wlroots
screen-sharing portal. On first login select Labwc in LXQt Session Settings.
Your compositor preferences remain editable there. X11 can also be enabled through
the normal NixOS X server options.

Twenty-six upstream LXQt repositories are locked to immutable default-branch Git
commits, including the build tools. Twenty-five runtime components are retained.
PCManFM-Qt and libfm-qt remain for desktop icons and wallpaper; optional apps such
as QTerminal, LXImage-Qt and the archive manager are excluded. Labwc, Qt, KDE
Frameworks and other base dependencies use NixOS packages and official binaries.

The private LXQt scope is passed only to matching desktop and portal modules.
Normal host applications keep their original derivations. A complete public NixOS
fixture checks that isolation and the Wayland session, builds the full closure,
and is fetched on a fresh runner with compilation disabled before publication.
This checks package integration, not an interactive graphical boot.

Only runtime closures and the public reference system are uploaded and retained.
Build helpers stay on the builder. Storage accounting counts shared paths once,
excludes official-cache paths and applies the shared 4 GiB runtime / 4.75 GiB
transition budgets. See the root README for installation and storage details.
