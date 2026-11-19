{
  lib,
  fetchFromGitHub,
  rustPlatform,
  libcosmicAppHook,
  stdenv,
  glib,
  just,
  nix-update-script,
  shared-mime-info,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-files";
  version = "1.11.0-unstable-2026-11-19";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-files";
    rev = "84a32e1eed33b1e017c8a653bfe1c2d5a13a711a";
    hash = "sha256-bp2z2Pmb6NZDJEbZFCAag1SmjSWmUGVUhKdVF3nGvAc=";
  };

  cargoHash = "sha256-H0T/5PP9RSOUG7OW+rD/7b6dAjDVePGDhJN1ENr76Pc=";

  nativeBuildInputs = [
    libcosmicAppHook
    just
  ];
  buildInputs = [ glib ];

  # TODO: uncomment and remove phases below if these packages can ever be built at the same time
  # NOTE: this causes issues with the desktop instance linking to a window tab when cosmic-files is opened, see <https://github.com/lilyinstarlight/nixos-cosmic/issues/591>
  #cargoBuildFlags = [
  #  "--package"
  #  "cosmic-files"
  #  "--package"
  #  "cosmic-files-applet"
  #];
  # cargoTestFlags = [
  #  "--package"
  #  "cosmic-files"
  #  "--package"
  #  "cosmic-files-applet"
  # ];

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "cargo-target-dir"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}"
  ];

  # TODO: remove next two phases if these packages can ever be built at the same time
  buildPhase = ''
    baseCargoBuildFlags="$cargoBuildFlags"
    cargoBuildFlags="$baseCargoBuildFlags --package cosmic-files"
    runHook cargoBuildHook
    cargoBuildFlags="$baseCargoBuildFlags --package cosmic-files-applet"
    runHook cargoBuildHook
    cargoBuildFlags="$baseCargoBuildFlags --package cosmic-files-thumbnailer"
    runHook cargoBuildHook
  '';

  checkPhase = ''
    export XDG_DATA_DIRS=${shared-mime-info}/share''${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}
    baseCargoTestFlags="$cargoTestFlags"
    # cargoCheckHook prepends to checkFlags, so isolate each invocation.
    cargoTestFlags="$baseCargoTestFlags --package cosmic-files"
    (runHook cargoCheckHook)
    cargoTestFlags="$baseCargoTestFlags --package cosmic-files-applet"
    (runHook cargoCheckHook)
    cargoTestFlags="$baseCargoTestFlags --package cosmic-files-thumbnailer"
    (runHook cargoCheckHook)
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-files";
    description = "File Manager for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-files";
  };
}
