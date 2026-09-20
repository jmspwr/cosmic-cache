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
  appPaths =
    p:
    builtins.mapAttrs (_: d: d.outPath) (
      p.lib.getAttrs [ "easyeffects" "nautilus" "gnome-text-editor" "gnome-console" "epiphany" ] p
    );
  applications = appPaths system.pkgs;
  installed = map (p: p.outPath) system.config.environment.systemPackages;
  packages = import ./packages.nix;
in
assert applications == appPaths baseline;
assert !system.config.services.gnome.core-apps.enable;
assert !(builtins.elem applications.nautilus installed);
assert builtins.elem packages.desktop.gnome-shell.outPath installed;
assert builtins.elem packages.desktop.gnome-settings-daemon.outPath installed;
{
  inherit applications;
  systemDerivation = system.config.system.build.toplevel.drvPath;
  systemPath = system.config.system.build.toplevel.outPath;
}
