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
  version = "1.12.0-unstable-2026-11-24";

  __structuredAttrs = true;

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-viewer";
    rev = "067c4fd0dba16a57a029aff40a0410af45bbe580";
    hash = "sha256-AZ1ZJcwDFoU/FiXJKP0rjBLO76xdtUBo1W7i1TwsH68=";
  };

  cargoHash = "sha256-h7cPpTZAgvKslsvuuVFTxZflKiNMqrZjhAVGI/VGebk=";

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
