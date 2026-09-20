let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  pkgs = import (fetchTarball { inherit (snapshot) url sha256; }) {
    system = "x86_64-linux";
    config = { };
  };
  kdePackages = pkgs.kdePackages.overrideScope (
    _: previous: {
      sources =
        previous.sources
        // builtins.mapAttrs (
          _: source: (pkgs.fetchzip { inherit (source) url sha256; }) // { inherit (source) version; }
        ) (snapshot.gitSources or { });
    }
  );
  pick = names: pkgs.lib.getAttrs names kdePackages;
in
{
  inherit pkgs kdePackages;
  inherit (pkgs) cachix;
  plasma = pick snapshot.plasma;
  selected = pick snapshot.selected;
  provided = pick snapshot.needed;
  # Debug symbols also retain source trees. Keep the derivations unchanged so
  # existing binaries remain reusable; publish every other output for CI/users.
  outputs = builtins.mapAttrs (_: p: map (o: p.${o}) (builtins.filter (o: o != "debug") p.outputs)) (
    pick snapshot.needed
  );
}
