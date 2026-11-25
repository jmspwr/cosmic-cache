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
  version = "1.12.0-unstable-2026-11-24";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-initial-setup";
    rev = "edf9290b601d0ebcf432cb858479309246221a1f";
    hash = "sha256-OLannXvC8n7Dom5WBWY4b1UAgC3RcBXtG5ScPYz9B+c=";
  };

  cargoHash = "sha256-4Vl360Gzz34uE9nqIknjW/5y1YdCp6zndvxtVrqtLa0=";

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
