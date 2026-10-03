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
  version = "1.9.0-unstable-2026-09-30";

  __structuredAttrs = true;

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-viewer";
    rev = "f3c21b635b10f4d23d4718836ba2ca80ee89d0e7";
    hash = "sha256-czsJGpzQn/frh0h8YyQcQCSNsR237p/ZdR4lr5/C+F4=";
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
