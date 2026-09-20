let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  upstream = builtins.getFlake snapshot.url;
  inherit (upstream.inputs.nixpkgs) lib;
  packages = upstream.packages.x86_64-linux;
  selected =
    name:
    (
      lib.hasPrefix "cosmic-" name && !lib.hasPrefix "cosmic-ext-" name
      || builtins.elem name [
        "cutecosmic"
        "pop-launcher"
        "xdg-desktop-portal-cosmic"
      ]
    )
    && name != "cosmic-applibrary";
in
lib.filterAttrs (name: _: selected name) packages
