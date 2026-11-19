{
  lib,
  fetchFromGitHub,
  rustPlatform,
  libcosmicAppHook,
  libinput,
  pkg-config,
  udev,
  openssl,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-initial-setup";
  version = "1.11.0-unstable-2026-11-19";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-initial-setup";
    rev = "27b79e72cdc84fa8698999caa74db29ba08938f8";
    hash = "sha256-7jHZs4zCDbzYorjsxuBi5zofSfsFTY05+xMaDHGeHdk=";
  };

  cargoHash = "sha256-1pmYtJYaekY58hjUh61JVQeNYQYUWUywStD9TtJ1eoI=";

  buildFeatures = [ "nixos" ];

  auditable = false;

  nativeBuildInputs = [
    libcosmicAppHook
    pkg-config
  ];
  buildInputs = [
    openssl
    libinput
    udev
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    description = "COSMIC Initial Setup";
    homepage = "https://github.com/pop-os/cosmic-initial-setup";
    license = lib.licenses.gpl3Only;
    mainProgram = "cosmic-initial-setup";
    platforms = lib.platforms.linux;
  };
}
