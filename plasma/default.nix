{ pkgs, lib, ... }:
let
  cache = builtins.fromJSON (builtins.readFile ../cache.json);
  proof = builtins.fromJSON (builtins.readFile ./cache-proof.json);
  packages = import ./packages.nix;
  plasmaOverlay = _: _: { inherit (packages) kdePackages; };
in
{
  # The host module may request packages removed from this newer KDE scope.
  # Import the matching module as a function so disabling the host's path also
  # works when the host and packaging snapshot happen to be the same Nixpkgs.
  disabledModules = [ "services/desktop-managers/plasma6.nix" ];
  imports = [
    (import (packages.pkgs.path + "/nixos/modules/services/desktop-managers/plasma6.nix"))
  ];
  assertions = [
    {
      assertion = pkgs.stdenv.hostPlatform.system == "x86_64-linux";
      message = "This Plasma cache publishes x86_64-linux packages only.";
    }
    {
      assertion = builtins.all (name: pkgs.kdePackages.${name}.outPath == proof.packages.${name}.path) (
        builtins.attrNames packages.selected
      );
      message = "The Plasma packages differ from the verified cache snapshot.";
    }
  ];
  nixpkgs.overlays = lib.mkAfter [ plasmaOverlay ];
  nix.settings = {
    extra-substituters = [ cache.uri ];
    extra-trusted-public-keys = cache.publicSigningKeys;
  };
}
