{
  config,
  pkgs,
  lib,
  ...
}:
let
  cache = builtins.fromJSON (builtins.readFile ../cache.json);
  proof = builtins.fromJSON (builtins.readFile ./cache-proof.json);
  packages = import ./packages.nix;
  upstream = import (packages.pkgs.path + "/nixos/modules/services/desktop-managers/plasma6.nix");
  modulePkgs = import ./module-packages.nix {
    hostPkgs = pkgs;
    desktop = packages.provided;
  };
  promised = builtins.mapAttrs (_: p: p.outPath) packages.provided;
  installed =
    config.environment.systemPackages
    ++ config.xdg.portal.extraPortals
    ++ config.services.displayManager.sessionPackages;
in
{
  # The host module may request packages removed from this newer KDE scope.
  # Import the matching module as a function so disabling the host's path also
  # works when the host and packaging snapshot happen to be the same Nixpkgs.
  disabledModules = [ "services/desktop-managers/plasma6.nix" ];
  imports = [
    (
      {
        config,
        lib,
        pkgs,
        utils,
        ...
      }@args:
      upstream (args // { pkgs = modulePkgs; })
    )
  ];
  assertions = [
    {
      assertion = pkgs.stdenv.hostPlatform.system == "x86_64-linux";
      message = "This Plasma cache publishes x86_64-linux packages only.";
    }
    {
      assertion = builtins.all (name: promised.${name} == proof.packages.${name}.path) (
        builtins.attrNames packages.provided
      );
      message = "The Plasma packages differ from the verified cache snapshot.";
    }
    {
      assertion =
        !config.services.desktopManager.plasma6.enable
        || builtins.all (
          p:
          let
            name = p.pname or "";
          in
          !(builtins.hasAttr name promised)
          || builtins.elem p.outPath (map toString packages.outputs.${name})
          # Qt5 themes deliberately remain the host's prebuilt variants.
          || builtins.elem p.outPath [
            (toString pkgs.kdePackages.breeze.qt5)
            (toString pkgs.kdePackages.plasma-integration.qt5)
          ]
        ) installed;
      message = "Another module installed Plasma components that conflict with the verified desktop.";
    }
  ];
  nix.settings = {
    extra-substituters = [ cache.uri ];
    extra-trusted-public-keys = cache.publicSigningKeys;
  };
}
