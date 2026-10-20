{
  lib,
  fetchFromGitHub,
  rustPlatform,
  libcosmicAppHook,
  stdenv,
  glib,
  just,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-files";
  version = "1.10.0-unstable-2026-10-20";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-files";
    rev = "3cc4b8003e8d08349c7ced8a9cdd10cdfa45d38c";
    hash = "sha256-kPiOaFkOqZxy2De3ln3T/chtKLQWkT4469flb62AOoE=";
  };

  cargoHash = "sha256-W9J736EyQ5o8WlQDYwmE1B4uD0/TgnF+OL5M/oidbnE=";

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
