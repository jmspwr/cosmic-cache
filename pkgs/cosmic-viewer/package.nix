{
  lib,
  fetchFromGitHub,
  just,
  libcosmicAppHook,
  libheif,
  libjpeg_turbo,
  nix-update-script,
  pkg-config,
  rustPlatform,
  stdenv,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-viewer";
  version = "1.9.0-unstable-2026-10-07";

  __structuredAttrs = true;

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-viewer";
    rev = "77ba62deb7027217efab1999e90670f3c89c5a02";
    hash = "sha256-k81AVE8KP6bRu4NBtFFmNELiM74bIAbOmAkAIHvfPyM=";
  };

  cargoHash = "sha256-KQUfeVp8I20ie8Nl4izWlSLN26AJEbsgWSDITxAOxLg=";

  postPatch = ''
    substituteInPlace Cargo.toml \
      --replace-fail '"embedded-libheif",' ""
  '';

  nativeBuildInputs = [
    # rustPlatform.bindgenHook
    just
    libcosmicAppHook
    pkg-config
  ];
  buildInputs = [
    libheif
    libjpeg_turbo
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  env.TURBOJPEG_SOURCE = "pkg-config";

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
    homepage = "https://github.com/pop-os/cosmic-viewer";
    description = "Image viewer for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-viewer";
  };
}
