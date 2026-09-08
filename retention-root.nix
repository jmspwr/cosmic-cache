let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  upstream = builtins.getFlake snapshot.url;
  pkgs = upstream.inputs.nixpkgs.legacyPackages.x86_64-linux;
  packages = import ./packages.nix;
in pkgs.writeText "cosmic-cached-runtime-roots" (pkgs.lib.concatMapStringsSep "\n" (p: "${p.out}") (builtins.attrValues packages))
