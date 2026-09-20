let
  packages = import ./packages.nix;
  outputs = builtins.concatLists (builtins.attrValues packages.outputs);
  proof = builtins.fromJSON (builtins.readFile ./cache-proof.json);
  references = map (system: builtins.storePath system.systemPath) (
    builtins.attrValues proof.referenceSystems
  );
in
packages.pkgs.writeText "plasma-cached-outputs" (
  packages.pkgs.lib.concatMapStringsSep "\n" toString (outputs ++ references)
)
