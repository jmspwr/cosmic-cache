{
  lib,
  fetchFromGitHub,
  just,
  libcosmicAppHook,
  nix-update-script,
  pkg-config,
  rustPlatform,
  stdenv,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-monitor";
  version = "1.12.0-unstable-2026-11-24";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-monitor";
    rev = "41302aae87edd69ae07de173cfa62d9e95278c86";
    hash = "sha256-poz+MQdeVYkzzz1I94Bku/EgdtGiqKswA2cU928tzoE=";
  };

  cargoHash = "sha256-xgywjLnH025PJaIhTiDkaRQCr3YzNVbG1WGmlzbd924=";

  nativeBuildInputs = [
    libcosmicAppHook
    just
    pkg-config
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/cosmic-monitor"
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-monitor";
    description = "COSMIC System Monitor";
    license = lib.licenses.gpl3Only;
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-monitor";
  };
}
