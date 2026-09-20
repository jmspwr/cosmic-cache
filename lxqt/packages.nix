let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  pkgs = import (fetchTarball { inherit (snapshot) url sha256; }) {
    system = "x86_64-linux";
    config = { };
  };
  scope = pkgs.lxqt.overrideScope (
    self: prev:
    builtins.mapAttrs (
      name: source:
      prev.${name}.overrideAttrs (old: {
        version = old.version + "-git." + builtins.substring 0 12 source.revision;
        src = pkgs.fetchzip { inherit (source) url sha256; };
        postPatch = builtins.replaceStrings [ "lxqt-hyprland.conf" ] [ "lxqt-hyprland.lua" ] (
          old.postPatch or ""
        );
      })
    ) snapshot.sources
  );
  # Build tools participate in the source lock, but are not retained as runtime roots.
  desktop = pkgs.lib.getAttrs (builtins.filter (n: n != "lxqt-build-tools") (
    builtins.attrNames snapshot.sources
  )) scope;
  runtime = builtins.attrValues (builtins.mapAttrs (_: p: p.out) desktop);
in
{
  inherit
    pkgs
    scope
    desktop
    runtime
    ;
  inherit (pkgs) cachix;
}
