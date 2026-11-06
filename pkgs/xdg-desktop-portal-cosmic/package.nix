{
  lib,
  stdenv,
  rustPlatform,
  fetchFromGitHub,
  just,
  libcosmicAppHook,
  util-linux,
  libgbm ? null,
  mesa,
  pipewire,
  pkg-config,
  gst_all_1,
  nix-update-script,
}:

rustPlatform.buildRustPackage rec {
  pname = "xdg-desktop-portal-cosmic";
  version = "1.11.0-unstable-2026-11-06";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "xdg-desktop-portal-cosmic";
    rev = "67624f8eb8fefb38dd398b929662c6b361392704";
    hash = "sha256-3R0gbLZiVq5afBggCxrLJ4wvnrRHT1ohSWwvK3KOfO0=";
  };

  cargoHash = "sha256-/ftXuX3N1wwmhSCmpJd2Ei/quH5AucOKsTbGGI4NQx8=";

  separateDebugInfo = true;

  nativeBuildInputs = [
    libcosmicAppHook
    rustPlatform.bindgenHook
    just
    pkg-config
    util-linux
  ];
  buildInputs = [
    (if libgbm != null then libgbm else mesa)
    pipewire
  ];
  checkInputs = [ gst_all_1.gstreamer ];

  env.VERGEN_GIT_SHA = src.rev;

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "bin-src"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}/release/xdg-desktop-portal-cosmic"
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/xdg-desktop-portal-cosmic";
    description = "XDG Desktop Portal for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    mainProgram = "xdg-desktop-portal-cosmic";
    platforms = lib.platforms.linux;
  };
}
