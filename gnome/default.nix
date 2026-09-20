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
  modulePkgs =
    pkgs
    // packages.desktop
    // {
      gnome-extensions-app = pkgs.gnome-extensions-app or packages.pkgs.gnome-extensions-app;
      gnome = pkgs.gnome // {
        nixos-gsettings-overrides = packages.pkgs.gnome.nixos-gsettings-overrides.override {
          inherit (packages.desktop) gnome-shell gsettings-desktop-schemas;
        };
      };
    };
  desktopModule = "services/desktop-managers/gnome.nix";
  settingsModule = "services/desktops/gnome/gnome-settings-daemon.nix";
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
    settingsModule
  ];
  imports = [
    (wrap desktopModule)
    (wrap settingsModule)
  ];
  # Upstream uses mkDefault true; a normal user declaration still wins over 900.
  services.gnome.core-apps.enable = lib.mkOverride 900 false;
  assertions = [
    {
      assertion = pkgs.stdenv.hostPlatform.system == "x86_64-linux";
      message = "This GNOME cache publishes x86_64-linux packages only.";
    }
    {
      assertion = builtins.all (name: packages.desktop.${name}.outPath == proof.packages.${name}.path) (
        builtins.attrNames packages.desktop
      );
      message = "The GNOME packages differ from the verified cache snapshot.";
    }
    {
      assertion =
        !config.services.desktopManager.gnome.enable
        || builtins.elem packages.desktop.gnome-shell.outPath (
          map (p: p.outPath) config.environment.systemPackages
        );
      message = "The GNOME session does not use the verified Git shell.";
    }
  ];
  nix.settings = {
    extra-substituters = [ cache.uri ];
    extra-trusted-public-keys = cache.publicSigningKeys;
  };
}
