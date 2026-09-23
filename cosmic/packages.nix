let
  snapshot = builtins.fromJSON (builtins.readFile ./snapshot.json);
  upstream = builtins.getFlake snapshot.url;
  inherit (upstream.inputs.nixpkgs) lib;
  recipe = name: builtins.readFile (upstream + "/pkgs/${name}/package.nix");
  # TEMPORARY: pop-os/cosmic-files b326e48 (21 Sep 2026) added a cosmic-files-thumbnailer
  # workspace binary that `just install` requires, but the upstream recipe neither builds it
  # nor points just at it. This self-removes: it applies only while the recipe never mentions
  # the thumbnailer, so the upstream fix silently supersedes it. Delete once that has happened.
  fixes.cosmic-files =
    p:
    if lib.hasInfix "thumbnailer" (recipe "cosmic-files") then
      p
    else
      p.overrideAttrs (o: {
        buildPhase = o.buildPhase + ''
          cargoBuildFlags="$baseCargoBuildFlags --package cosmic-files-thumbnailer"
          runHook cargoBuildHook
        '';
        justFlags = o.justFlags ++ [
          "--set"
          "thumbnailer-bin-src"
          "${lib.findFirst (lib.hasSuffix "/release/cosmic-files") null o.justFlags}-thumbnailer"
        ];
      });
  packages = builtins.mapAttrs (name: p: (fixes.${name} or (x: x)) p) upstream.packages.x86_64-linux;
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
