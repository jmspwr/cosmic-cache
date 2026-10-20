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
  version = "1.10.0-unstable-2026-10-20";

  __structuredAttrs = true;

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-viewer";
    rev = "300210f1c7d86ba14a43602e40dd5fe1deb16703";
    hash = "sha256-HR/GQT8RbLBdT/jY1XgaUPaVeUJYx8SfhjuwLV+CSOo=";
  };

  cargoHash = "sha256-fUtTCA5a3kn3O8O2aUoUA+23Yz3ynSIiDqxWPnDLi7o=";

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
