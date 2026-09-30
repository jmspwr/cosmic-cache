{
  lib,
  fetchFromGitHub,
  rustPlatform,
  libcosmicAppHook,
  bash,
  just,
  stdenv,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-idle";
  version = "1.9.0-unstable-2026-09-30";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-idle";
    rev = "b3693ea1cfbef12e5369073c2d43e7e82936fd4d";
    hash = "sha256-hX1yXfoQXP6e/v4IWAKXUz9hN0cqR1ylX5I0zvzUJVQ=";
  };

  cargoHash = "sha256-wAjFC6qAC3nllbnZf0KVaZTEztNYo6GTvwcp5FYmXLw=";

  nativeBuildInputs = [
    libcosmicAppHook
    just
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/cosmic-idle"
  ];

  postPatch = ''
    substituteInPlace src/main.rs --replace-fail '"/bin/sh"' '"${lib.getExe bash}"'
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-idle";
    description = "Idle daemon for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-idle";
  };
}
