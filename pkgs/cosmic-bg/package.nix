{
  lib,
  fetchFromGitHub,
  rustPlatform,
  libcosmicAppHook,
  dav1d,
  just,
  nasm,
  pkg-config,
  stdenv,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-bg";
  version = "1.9.0-unstable-2026-09-30";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-bg";
    rev = "5b585e2e91b17e84973efe2d4de93b64486f9344";
    hash = "sha256-leSGrBCpclPYEkjfOTon1RieW0I09cuqcc43Z5Knvdg=";
  };

  cargoHash = "sha256-4jXd7uJEREPqrJvpt5aAf+3V+8+XViDb8zqmgq+qvU4=";

  nativeBuildInputs = [
    libcosmicAppHook
    just
    nasm
    pkg-config
  ];

  buildInputs = [
    dav1d
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/cosmic-bg"
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-bg";
    description = "Applies Background for the COSMIC Desktop Environment";
    license = lib.licenses.mpl20;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-bg";
  };
}
