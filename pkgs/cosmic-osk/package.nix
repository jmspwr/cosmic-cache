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
  version = "1.11.0-unstable-2026-10-20";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-osk";
    rev = "6b146a2b0a23d88ae84223ad06c6813bda5a9386";
    hash = "sha256-rw8BMxgr5MzmCj8THSOr/TE2GsAMxgC2YXgONVppYzc=";
  };

  cargoHash = "sha256-3aAaceBp6fDQc0KDwY5L922tGvK+5z5Kbzyy+De6Hkg=";

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
