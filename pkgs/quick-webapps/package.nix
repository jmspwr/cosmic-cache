{
  lib,
  fetchFromGitHub,
  libcosmicAppHook,
  rustPlatform,
  gtk3,
  glib,
  just,
  pkg-config,
  webkitgtk_4_1,
  stdenv,
  nix-update-script,
}:

rustPlatform.buildRustPackage rec {
  pname = "quick-webapps";
  version = "3.0.0-unstable-2026-09-27";

  src = fetchFromGitHub {
    owner = "cosmic-utils";
    repo = "web-apps";
    rev = "a291403f85cad261cb4727e6fbe12dd65d205ff8";
    hash = "sha256-EqjelMSwLxEAzANW+rC09UJNSKej+OtQuU7sPfinvoo=";
  };

  cargoHash = "sha256-gZwSM2J7NW36FktUzWS1Os2rGf9jNE8zdJu5ZVy9hQw=";

  nativeBuildInputs = [
    libcosmicAppHook
    just
    pkg-config
  ];

  buildInputs = [
    gtk3
    glib
    webkitgtk_4_1
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "base-dir"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/dev-heppen-webapps"
    "--set"
    "webview-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/dev-heppen-webapps-webview"
  ];

  env.VERGEN_GIT_SHA = src.rev;

  passthru.updateScript = nix-update-script { };

  meta = {
    homepage = "https://github.com/cosmic-utils/web-apps";
    description = "Web app manager for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "quick-webapps";
  };
}
