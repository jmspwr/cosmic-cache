{ host }:
let
  system = "x86_64-linux";
  baseline = import host { inherit system; };
  evaluated = import (host + "/nixos/lib/eval-config.nix") {
    inherit system;
    modules = [
      ./default.nix
      ./profile.nix
    ];
  };
  inherit (evaluated) config pkgs;
  packages = import ./packages.nix;
  names = builtins.attrNames packages;
  sessions = builtins.concatMap (
    p: p.providedSessions or [ ]
  ) config.services.displayManager.sessionPackages;
in
assert builtins.all (a: a.assertion) config.assertions;
assert builtins.all (n: pkgs.${n}.outPath == packages.${n}.outPath) names;
assert pkgs.easyeffects.outPath == baseline.easyeffects.outPath;
assert builtins.elem "cosmic" sessions;
assert
  config.services.displayManager.cosmic-greeter.package.outPath == packages.cosmic-greeter.outPath;
{
  systemPath = config.system.build.toplevel.outPath;
  systemDerivation = config.system.build.toplevel.drvPath;
  inherit sessions;
  packages = builtins.mapAttrs (_: p: p.outPath) packages;
}
