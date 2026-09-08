let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  compat = builtins.fromJSON (builtins.readFile ./compat.json);
  upstream = builtins.getFlake snapshot.url;
  lib = upstream.inputs.nixpkgs.lib;
  nixpkgs = upstream.inputs.nixpkgs.legacyPackages.x86_64-linux;
  base = upstream.packages.x86_64-linux;
  recipe = upstream.outPath + "/pkgs/cosmic-comp/package.nix";
  canOverrideLibdisplayInfo =
    builtins.pathExists recipe
    && lib.hasInfix "libdisplay-info," (builtins.readFile recipe);
  packages = base // (if (compat.cosmicCompLibdisplayInfo03 or false) && canOverrideLibdisplayInfo then {
    cosmic-comp = base.cosmic-comp.override { libdisplay-info = nixpkgs.libdisplay-info_0_3; };
  } else { });
  names = builtins.filter (name:
    ((builtins.match "cosmic-.*" name != null && builtins.match "cosmic-ext-.*" name == null)
      || builtins.elem name [ "pop-launcher" "xdg-desktop-portal-cosmic" "cutecosmic" ])
    && name != "cosmic-applibrary"
  ) (builtins.attrNames packages);
in builtins.listToAttrs (map (name: { inherit name; value = packages.${name}; }) names)
