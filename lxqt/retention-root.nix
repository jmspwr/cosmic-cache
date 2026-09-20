let
  p = import ./packages.nix;
  proof = builtins.fromJSON (builtins.readFile ./cache-proof.json);
  references = map (s: builtins.storePath s.systemPath) (builtins.attrValues proof.referenceSystems);
in
p.pkgs.writeText "lxqt-runtime-roots" (
  p.pkgs.lib.concatMapStringsSep "\n" toString (p.runtime ++ references)
)
