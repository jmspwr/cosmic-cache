{ pkgs, lib, ... }:
let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  cache = builtins.fromJSON (builtins.readFile ./cache.json);
  upstream = builtins.getFlake snapshot.url;
  packages = import ./packages.nix;
  cosmicOverlay = final: prev: packages;
in
{
  imports = [
    (import (upstream.outPath + "/nixos") {
      nixpkgsPath = upstream.inputs.nixpkgs;
      inherit cosmicOverlay;
    })
  ];
  assertions = [
    {
      assertion = pkgs.stdenv.hostPlatform.system == "x86_64-linux";
      message = "This COSMIC cache publishes x86_64-linux packages only.";
    }
    {
      assertion = builtins.all
        (name: builtins.hasAttr name pkgs && pkgs.${name}.outPath == packages.${name}.outPath)
        (builtins.attrNames packages);
      message = "Another Nixpkgs overlay replaced one or more verified cached COSMIC packages.";
    }
  ];
  nixpkgs.overlays = lib.mkAfter [ cosmicOverlay ];
  nix.settings = {
    extra-substituters = [ cache.uri ];
    extra-trusted-public-keys = cache.publicSigningKeys;
  };
}
