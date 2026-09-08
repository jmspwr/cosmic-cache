# args from flake
{
  cosmicOverlay,
  nixpkgsPath,
}:

# module args
{
  lib,
  modulesPath,
  ...
}:

let
  unstableModulesPath = nixpkgsPath + "/nixos/modules";

  modules = basePath: lib.optionals (lib.versionOlder lib.trivial.version "25.11") [
    # depends on changes to geoclue not existing on 25.05
    (basePath + "/services/desktops/geoclue2.nix")
  ] ++ lib.optionals (lib.versionOlder lib.trivial.version "26.11") [
    # depends on changes to polkit not existing on 26.05
    (basePath + "/security/polkit.nix")
  ] ++ [
    (basePath + "/services/display-managers/cosmic-greeter.nix")
    (basePath + "/services/desktop-managers/cosmic.nix")
  ];
in
{
  imports = modules unstableModulesPath;

  disabledModules = lib.optionals (modulesPath != unstableModulesPath) (modules modulesPath);

  nixpkgs.overlays = [ cosmicOverlay ];
}
