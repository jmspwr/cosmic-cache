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
  version = "1.11.0-unstable-2026-10-30";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-files";
    rev = "3204c6aafee15dde29b79b9776e5b8dc65dc7de8";
    hash = "sha256-tX0Cv8sIBHgdOysJxa5n97G2unsmXDy2x5inF0IjSxk=";
  };

  cargoHash = "sha256-yjgrbJn/QjWXlAI4Pqo4QdE5T2jmIP37ftURosguRYE=";

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
