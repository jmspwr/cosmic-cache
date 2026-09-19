let
  packages = import ./packages.nix;
  outputs = builtins.concatLists (builtins.attrValues packages.outputs);
in
packages.pkgs.writeText "plasma-cached-outputs" (
  packages.pkgs.lib.concatMapStringsSep "\n" toString outputs
)
