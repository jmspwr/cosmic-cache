{
  lib,
  fetchFromGitHub,
  rustPlatform,
  just,
  libcosmicAppHook,
  libdisplay-info,
  libdisplay-info_0_3 ? libdisplay-info,
  libgbm ? null,
  libinput,
  mesa,
  pixman,
  pkg-config,
  seatd,
  stdenv,
  udev,
  xwayland,
  useXWayland ? true,
  systemd,
  useSystemd ? lib.meta.availableOn stdenv.hostPlatform systemd,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-comp";
  version = "1.11.0-unstable-2026-10-28";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-comp";
    rev = "9239866618d512c909301f60d337969e46ff466f";
    hash = "sha256-pAGyBGgKVGlXoFPfmacnD4PTsMzMud1289QlPc6mre4=";
  };

  cargoHash = "sha256-D9kykY+WGVcsm4Bgapw5r3vrc1xDuMM5v+1a1Pn13Qk=";

  separateDebugInfo = true;

  nativeBuildInputs = [
    libcosmicAppHook
    pkg-config
  ];
  buildInputs = [
    libdisplay-info_0_3
    (if libgbm != null then libgbm else mesa)
    libinput
    pixman
    seatd
    udev
  ] ++ lib.optional useSystemd systemd;

  # only default feature is systemd
  buildNoDefaultFeatures = !useSystemd;

  installPhase = ''
    runHook preInstall

    CARGO_TARGET_DIR=target/${stdenv.hostPlatform.rust.cargoShortTarget} ${lib.getExe just} --set prefix "$out" install

    runHook postInstall
  '';

  preFixup = lib.optionalString useXWayland ''
    libcosmicAppWrapperArgs+=(--prefix PATH : ${lib.makeBinPath [ xwayland ]})
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-comp";
    description = "Compositor for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-comp";
  };
}
