# Evaluate a complete representative system, including the host's service modules.
# Merely checking assertions/package identities misses lazy systemPackages errors.
{
  hostNixpkgs ? (import ./packages.nix).pkgs.path,
}:
let
  system = import (hostNixpkgs + "/nixos") {
    system = "x86_64-linux";
    configuration.imports = [
      ./default.nix
      ./profile.nix
    ];
  };
in
{
  systemDerivation = system.config.system.build.toplevel.drvPath;
}
