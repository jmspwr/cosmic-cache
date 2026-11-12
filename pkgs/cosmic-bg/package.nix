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
  version = "1.11.0-unstable-2026-11-12";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-bg";
    rev = "243990320904ac1f80f8888babd34e864f974bd0";
    hash = "sha256-Tk+CFKDzIvYuabVLJ998J4x4OTGG+6YBkFO03oRkNNE=";
  };

  cargoHash = "sha256-QBSKyHhtevaLM2v/1fRTMcveRsAtZ3DJYijeuzyLANQ=";

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
