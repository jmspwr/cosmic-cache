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
  version = "1.11.0-unstable-2026-11-03";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-comp";
    rev = "8e0b615f0e2fcfe082da19ec37528c7bc804d092";
    hash = "sha256-35q6iXhkPPFJS4HNcqGV9iQXWK3b4t5SAFMdsN1CRRE=";
  };

  cargoHash = "sha256-naEuGY14CuYl1aD9dTzgMVVPaapLYLuOH/XpJ36vLu0=";

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
