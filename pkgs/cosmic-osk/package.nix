{
  lib,
  fetchFromGitHub,
  just,
  libcosmicAppHook,
  nix-update-script,
  rustPlatform,
  stdenv,
  udev,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-osk";
  version = "1.9.0-unstable-2026-09-30";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-osk";
    rev = "e1ba4af0c75fd107c5d8d54b613f3137e47e7923";
    hash = "sha256-co/pMIfjXLH/lt1mdn61aRJdSznLfEGrtkLZwy9htuQ=";
  };

  cargoHash = "sha256-r5XlNx1GIy4gEiHX9QVYLEufRnuwxe9X4OBbz3tinIo=";

  nativeBuildInputs = [
    rustPlatform.bindgenHook
    libcosmicAppHook
    just
  ];
  buildInputs = [
    udev
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "cargo-target-dir"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}"
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-osk";
    description = "On screen keyboard for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-osk";
  };
}
