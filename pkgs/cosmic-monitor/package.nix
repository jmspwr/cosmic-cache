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
  version = "1.9.0-unstable-2026-09-30";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-monitor";
    rev = "343df86505bd5b624b2af4a8f588e429489e4ea9";
    hash = "sha256-na+SyGhspEGHx4gjUaNk+kqCWqGUysJzZ+uNI6LgUNw=";
  };

  cargoHash = "sha256-OM7oNcXuZmdnkdPexTQkHHAN4VxL3wdBqBuZp9vQLG8=";

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
