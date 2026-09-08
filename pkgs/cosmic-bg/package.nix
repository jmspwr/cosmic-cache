{
  lib,
  fetchFromGitHub,
  rustPlatform,
  libcosmicAppHook,
  dav1d,
  just,
  nasm,
  pkg-config,
  stdenv,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-bg";
  version = "1.7.0-unstable-2026-07-29";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-bg";
    rev = "1685f7fc99cbb9cbe981ac672d6451ba6faff7db";
    hash = "sha256-tvYVe3H99oB6NYzLjwzX+ccSFh54LAfvuLmFoCIaJp4=";
  };

  cargoHash = "sha256-j07BZ9JsY6UG9eXVxdn0CTWU8j/cGNA9lXrDsdF40lM=";

  nativeBuildInputs = [
    libcosmicAppHook
    just
    nasm
    pkg-config
  ];

  buildInputs = [
    dav1d
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/cosmic-bg"
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-bg";
    description = "Applies Background for the COSMIC Desktop Environment";
    license = lib.licenses.mpl20;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-bg";
  };
}
