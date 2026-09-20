let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  pkgs = import (fetchTarball { inherit (snapshot) url sha256; }) {
    system = "x86_64-linux";
    config = { };
  };
  desktop = pkgs.lib.fix (
    self:
    builtins.mapAttrs (
      name: source:
      (pkgs.${name}.override (builtins.intersectAttrs (pkgs.lib.functionArgs pkgs.${name}.override) self))
      .overrideAttrs
        (old: {
          version = source.version + "-git." + builtins.substring 0 12 source.revision;
          src = pkgs.fetchzip { inherit (source) url sha256; };
          postUnpack =
            (old.postUnpack or "")
            + pkgs.lib.concatMapStrings (s: ''
              mkdir -p "$sourceRoot/subprojects"
              rm -rf "$sourceRoot/${s.path}"
              cp -r ${pkgs.fetchzip { inherit (s) url sha256; }} "$sourceRoot/${s.path}"
              chmod -R u+w "$sourceRoot/${s.path}"
            '') source.subprojects;
          # Git archives do not contain the generated CSS shipped in release tarballs.
          postPatch =
            builtins.replaceStrings [ "rm data/theme/gnome-shell-" ] [ "rm -f data/theme/gnome-shell-" ]
              (old.postPatch or "");
        })
    ) snapshot.sources
  );
  runtime = builtins.concatLists (
    builtins.attrValues (
      builtins.mapAttrs (
        name: p: [ p.out ] ++ pkgs.lib.optional (name == "gnome-session") p.sessions
      ) desktop
    )
  );
in
{
  inherit desktop pkgs runtime;
  inherit (pkgs) cachix;
}
