let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  upstream = builtins.getFlake snapshot.url;
  packages = upstream.packages.x86_64-linux;
  names = builtins.filter (name:
    ((builtins.match "cosmic-.*" name != null && builtins.match "cosmic-ext-.*" name == null)
      || builtins.elem name [ "pop-launcher" "xdg-desktop-portal-cosmic" "cutecosmic" ])
    && name != "cosmic-applibrary"
  ) (builtins.attrNames packages);
in builtins.listToAttrs (map (name: { inherit name; value = packages.${name}; }) names)
