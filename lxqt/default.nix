{
  config,
  pkgs,
  lib,
  ...
}:
let
  packages = import ./packages.nix;
  proof = builtins.fromJSON (builtins.readFile ./cache-proof.json);
  cache = builtins.fromJSON (builtins.readFile ../cache.json);
  modulePkgs = pkgs // {
    lxqt = packages.scope;
  };
  desktopModule = "services/x11/desktop-managers/lxqt.nix";
  portalModule = "config/xdg/portals/lxqt.nix";
  wrap =
    path:
    (
      {
        config,
        lib,
        pkgs,
        utils,
        ...
      }@args:
      (import (packages.pkgs.path + "/nixos/modules/${path}")) (args // { pkgs = modulePkgs; })
    );
in
{
  disabledModules = [
    desktopModule
    portalModule
  ];
  imports = [
    (wrap desktopModule)
    (wrap portalModule)
  ];
  config = lib.mkMerge [
    {
      environment.lxqt.excludePackages = lib.mkDefault packages.scope.optionalPackages;
      assertions = [
        {
          assertion = pkgs.stdenv.hostPlatform.system == "x86_64-linux";
          message = "This LXQt cache publishes x86_64-linux packages only.";
        }
        {
          assertion = builtins.all (name: packages.desktop.${name}.outPath == proof.packages.${name}.path) (
            builtins.attrNames packages.desktop
          );
          message = "The LXQt packages differ from the verified cache snapshot.";
        }
      ];
      nix.settings = {
        extra-substituters = [ cache.uri ];
        extra-trusted-public-keys = cache.publicSigningKeys;
      };
    }
    (lib.mkIf config.services.xserver.desktopManager.lxqt.enable {
      programs.labwc.enable = lib.mkDefault true;
      programs.swaylock.enable = lib.mkDefault true;
      services.displayManager.sessionPackages = [ packages.scope.lxqt-wayland-session ];
      xdg.portal = {
        wlr.enable = lib.mkDefault true;
        config.lxqt = {
          "org.freedesktop.impl.portal.ScreenCast" = lib.mkDefault [ "wlr" ];
          "org.freedesktop.impl.portal.Screenshot" = lib.mkDefault [ "wlr" ];
        };
      };
      environment.systemPackages = [ pkgs.slurp ];
    })
  ];
}
