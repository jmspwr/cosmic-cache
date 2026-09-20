{ pkgs, lib, ... }:
let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  cache = builtins.fromJSON (builtins.readFile ../cache.json);
  upstream = builtins.getFlake snapshot.url;
  packages = import ./packages.nix;
  proof = builtins.fromJSON (builtins.readFile ./cache-proof.json);
  cosmicOverlay = _: _: packages;
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
      assertion =
        proof.schema == 3
        && snapshot.schema == 2
        && lib.hasSuffix "/${proof.revision}" snapshot.url
        && builtins.attrNames packages == builtins.attrNames proof.packages;
      message = "The COSMIC snapshot and cache proof do not match.";
    }
    {
      assertion = pkgs.stdenv.hostPlatform.system == "x86_64-linux";
      message = "This COSMIC cache publishes x86_64-linux packages only.";
    }
    {
      assertion = builtins.all (
        name: builtins.hasAttr name pkgs && pkgs.${name}.outPath == proof.packages.${name}.path
      ) (builtins.attrNames packages);
      message = "Another Nixpkgs overlay replaced one or more verified cached COSMIC packages.";
    }
  ];
  nixpkgs.overlays = lib.mkAfter [ cosmicOverlay ];
  nix.settings = {
    experimental-features = [
      "nix-command"
      "flakes"
    ];
    extra-substituters = [ cache.uri ];
    extra-trusted-public-keys = cache.publicSigningKeys;
  };
}
