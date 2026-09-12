let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  upstream = builtins.getFlake snapshot.url;
  inherit (upstream.inputs.nixpkgs) lib;
  nixpkgs = upstream.inputs.nixpkgs.legacyPackages.x86_64-linux;
  base = upstream.packages.x86_64-linux;
  packages = base // lib.optionalAttrs (lib.functionArgs base.cosmic-comp.override ? libdisplay-info) {
    cosmic-comp = base.cosmic-comp.override { libdisplay-info = nixpkgs.libdisplay-info_0_3; };
  };
  selected = name:
    (lib.hasPrefix "cosmic-" name && !lib.hasPrefix "cosmic-ext-" name
      || builtins.elem name [ "cutecosmic" "pop-launcher" "xdg-desktop-portal-cosmic" ])
    && name != "cosmic-applibrary";
in lib.filterAttrs (name: _: selected name) packages
