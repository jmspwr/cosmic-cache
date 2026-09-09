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
  version = "1.8.0-unstable-2026-09-01";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "xdg-desktop-portal-cosmic";
    rev = "abf258b86338185d2f7ecd243273ffc3deffca5f";
    hash = "sha256-UbWQSdC1GhizgFn9KMxJDT8rV8IaZ4hwDA0hQ14qc7o=";
  };

  cargoHash = "sha256-cENH+9M4irNfsSioeP3yX38Ux1ESO0KXtaiiK3XuEtA=";

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
