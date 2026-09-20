{
  previousRoots ? [ ],
}:
let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  upstream = builtins.getFlake snapshot.url;
  pkgs = upstream.inputs.nixpkgs.legacyPackages.x86_64-linux;
  packages = import ./packages.nix;
  proof = builtins.fromJSON (builtins.readFile ./cache-proof.json);
in
pkgs.writeText "cosmic-cache-runtime-roots" (
  pkgs.lib.concatStringsSep "\n" (
    map (p: "${p.out}") (builtins.attrValues packages)
    ++ map (p: builtins.storePath p.systemPath) (builtins.attrValues proof.referenceSystems)
    ++ map builtins.storePath previousRoots
  )
)
