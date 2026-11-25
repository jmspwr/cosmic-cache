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
  version = "1.12.0-unstable-2026-11-24";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-osk";
    rev = "588a52bd73c99c60714d3645ede583decbe78a20";
    hash = "sha256-STAsPrBHaiAZjGr6tlSzFKH0zq5K0ATRJUQFPGl/NKU=";
  };

  cargoHash = "sha256-mYXUMhdo9owHqnpZZlY1Rlr4qZAsGd/jILzp7hHpEUU=";

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
