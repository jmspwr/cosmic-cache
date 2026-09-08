{ pkgs, ... }:
let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  cache = builtins.fromJSON (builtins.readFile ./cache.json);
  upstream = builtins.getFlake snapshot.url;
  packages = import ./packages.nix;
in
{
  imports = [
    (import (upstream.outPath + "/nixos") {
      nixpkgsPath = upstream.inputs.nixpkgs;
      cosmicOverlay = final: prev: packages;
    })
  ];
  assertions = [{
    assertion = pkgs.stdenv.hostPlatform.system == "x86_64-linux";
    message = "This COSMIC cache publishes x86_64-linux packages only.";
  }];
  nix.settings = {
    substituters = [ cache.uri ];
    trusted-public-keys = cache.publicSigningKeys;
  };
}
