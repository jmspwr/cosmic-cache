{
  lib,
  fetchFromGitHub,
  just,
  libcosmicAppHook,
  nix-update-script,
  pkg-config,
  rustPlatform,
  stdenv,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-monitor";
  version = "1.8.0-unstable-2026-09-02";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-monitor";
    rev = "9ec3133c1be67a0f7041d678ff062f775a22e933";
    hash = "sha256-nItwje+QZkR0L+wOsmOVPJwo4THwiRLLvIFvH6XP31o=";
  };

  cargoHash = "sha256-HHKIXKyS1zDkNGbsEWiKghPqIsPKRUJtjxKuNfI6mak=";

  nativeBuildInputs = [
    libcosmicAppHook
    just
    pkg-config
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/cosmic-monitor"
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-monitor";
    description = "COSMIC System Monitor";
    license = lib.licenses.gpl3Only;
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-monitor";
  };
}
