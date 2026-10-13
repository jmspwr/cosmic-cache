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
  version = "3.0.0-unstable-2026-10-13";

  src = fetchFromGitHub {
    owner = "cosmic-utils";
    repo = "web-apps";
    rev = "4ac47a0202b935146cd00524c7184b51eb199bb7";
    hash = "sha256-Dj2U7M3uDHxcxveDKz/fxBOnLC4P73AL0On15OF2RAQ=";
  };

  cargoHash = "sha256-mKSUYLSPGIeOL50IkxcbQK0/Ol7APpFBgsQQ4LdFhHY=";

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
