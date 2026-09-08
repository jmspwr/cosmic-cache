let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  upstream = builtins.getFlake snapshot.url;
  nixpkgs = upstream.inputs.nixpkgs.legacyPackages.x86_64-linux;
  base = upstream.packages.x86_64-linux;
  packages = base // {
    cosmic-comp = base.cosmic-comp.override { libdisplay-info = nixpkgs.libdisplay-info_0_3; };
  };
  names = builtins.filter (name:
    ((builtins.match "cosmic-.*" name != null && builtins.match "cosmic-ext-.*" name == null)
      || builtins.elem name [ "pop-launcher" "xdg-desktop-portal-cosmic" "cutecosmic" ])
    && name != "cosmic-applibrary"
  ) (builtins.attrNames packages);
in builtins.listToAttrs (map (name: { inherit name; value = packages.${name}; }) names)
