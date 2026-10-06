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
  version = "1.9.0-unstable-2026-10-06";

  __structuredAttrs = true;

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-viewer";
    rev = "b7098f7f37d6db9d14589e0fa3b048ceb24e4175";
    hash = "sha256-W9UYrDCFemJogj34KS2+YWoupZm10RXhV/9SOCEWfyw=";
  };

  cargoHash = "sha256-vPUhFkDFIEJ+uHmCcc54jQVzks3orQdu2JUPEfIimOw=";

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
