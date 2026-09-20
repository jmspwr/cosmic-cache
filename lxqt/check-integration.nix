{
  hostNixpkgs ? (import ./packages.nix).pkgs.path,
}:
let
  baseline = import hostNixpkgs {
    system = "x86_64-linux";
    config = { };
  };
  system = import (hostNixpkgs + "/nixos") {
    system = "x86_64-linux";
    configuration.imports = [
      ./default.nix
      ./profile.nix
    ];
  };
  appPaths = p: {
    inherit
      (builtins.mapAttrs (_: d: d.outPath) {
        inherit (p) easyeffects;
        inherit (p.lxqt) qterminal lximage-qt lxqt-archiver;
        inherit (p.kdePackages) dolphin;
      })
      easyeffects
      qterminal
      lximage-qt
      lxqt-archiver
      dolphin
      ;
  };
  applications = appPaths system.pkgs;
  installed = map (p: p.outPath) system.config.environment.systemPackages;
  packages = import ./packages.nix;
in
assert applications == appPaths baseline;
assert builtins.all (p: !(builtins.elem p installed)) (builtins.attrValues applications);
assert builtins.elem packages.desktop.lxqt-panel.outPath installed;
assert builtins.elem packages.desktop.pcmanfm-qt.outPath installed;
assert builtins.elem packages.desktop.lxqt-wayland-session.outPath (
  map (p: p.outPath) system.config.services.displayManager.sessionPackages
);
{
  inherit applications;
  systemDerivation = system.config.system.build.toplevel.drvPath;
  systemPath = system.config.system.build.toplevel.outPath;
}
