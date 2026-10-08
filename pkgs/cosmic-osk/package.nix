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
  version = "1.10.0-unstable-2026-10-08";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-osk";
    rev = "3a4800a10b03efac1684817238922db5d6746403";
    hash = "sha256-Xf8d9c/pVeP5lpruB77onfJM8P5FPUNpmb5EZUhfI2Q=";
  };

  cargoHash = "sha256-PfI2w4M0OCGC2yVV9Q4xhN/ZQ/QZmvkZtlq0fzKMQ3M=";

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
