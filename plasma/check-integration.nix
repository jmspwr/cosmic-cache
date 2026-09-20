# Evaluate a complete representative system, including the host's service modules.
# Merely checking assertions/package identities misses lazy systemPackages errors.
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
    pkgs:
    builtins.mapAttrs (_: p: p.outPath) (
      {
        inherit (pkgs) easyeffects;
        breeze-qt5 = pkgs.kdePackages.breeze.qt5;
        plasma-integration-qt5 = pkgs.kdePackages.plasma-integration.qt5;
        kio-qt5 = pkgs.libsForQt5.__internalKF5.kio;
      }
      // pkgs.lib.getAttrs [
        "dolphin"
        "ark"
        "konsole"
        "kate"
        "elisa"
        "gwenview"
        "okular"
        "khelpcenter"
        "kio-extras"
        "akonadi"
        "kmail"
      ] pkgs.kdePackages
    );
  applications = appPaths system.pkgs;
  installed = map (p: p.outPath) system.config.environment.systemPackages;
  modulePkgs = import ./module-packages.nix {
    hostPkgs = system.pkgs;
    desktop = (import ./packages.nix).provided;
  };
in
assert applications == appPaths baseline;
assert appPaths modulePkgs == applications;
assert builtins.all (name: builtins.elem applications.${name} installed) [
  "easyeffects"
  "breeze-qt5"
  "plasma-integration-qt5"
];
assert builtins.all (name: !(builtins.elem applications.${name} installed)) [
  "dolphin"
  "ark"
  "konsole"
  "kate"
  "elisa"
  "gwenview"
  "okular"
  "khelpcenter"
];
{
  inherit applications;
  systemDerivation = system.config.system.build.toplevel.drvPath;
  systemPath = system.config.system.build.toplevel.outPath;
}
