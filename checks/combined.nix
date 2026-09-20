# Evaluate the four independently published consumers together, on one native host.
{
  desktops ? [
    "cosmic"
    "plasma"
    "gnome"
    "lxqt"
  ],
  modules ? map (
    d:
    (fetchTarball "https://github.com/jmspwr/desktop-cache/archive/${d}-cache.tar.gz")
    + "/${d}/default.nix"
  ) desktops,
  host ? fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz",
}:
let
  baseline = import host {
    system = "x86_64-linux";
    config = { };
  };
  s = import (host + "/nixos") {
    system = "x86_64-linux";
    configuration = {
      imports = modules;
      boot.isContainer = true;
      powerManagement.enable = true;
      networking.networkmanager.enable = true;
      services.desktopManager = {
        cosmic.enable = builtins.elem "cosmic" desktops;
        plasma6.enable = builtins.elem "plasma" desktops;
        gnome.enable = builtins.elem "gnome" desktops;
      };
      services.xserver.desktopManager.lxqt.enable = builtins.elem "lxqt" desktops;
      services.pipewire.enable = true;
      system.stateVersion = "25.11";
    };
  };
  applications = p: {
    inherit
      (builtins.mapAttrs (_: d: d.outPath) {
        inherit (p) easyeffects nautilus;
        inherit (p.kdePackages) dolphin;
        inherit (p.lxqt) qterminal;
      })
      easyeffects
      nautilus
      dolphin
      qterminal
      ;
  };
in
assert applications s.pkgs == applications baseline;
{
  systemDerivation = s.config.system.build.toplevel.drvPath;
  sessions = map (p: p.name) s.config.services.displayManager.sessionPackages;
  applications = applications s.pkgs;
}
