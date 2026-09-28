{
  lib,
  fetchFromGitHub,
  rustPlatform,
  geoclue2-with-demo-agent,
  libinput,
  libxkbcommon,
  openssl,
  patchelf,
  pkg-config,
  pipewire,
  udev,
  wayland,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-settings-daemon";
  version = "1.9.0-unstable-2026-09-28";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-settings-daemon";
    rev = "f22461b19ae03932df4234ceac28fd8b64ae6198";
    hash = "sha256-YHAm91qPAw1XBuarGqoLHS4LVmI0lZSuF3PmMtsyx9A=";
  };

  cargoHash = "sha256-edtRS56p1k8GhMM71R4lWDWFDmNjpkBSWBHrEEIxAJ8=";

  nativeBuildInputs = [
    rustPlatform.bindgenHook
    patchelf
    pkg-config
  ];
  buildInputs = [
    libinput
    libxkbcommon
    openssl
    pipewire
    udev
  ];

  env.GEOCLUE_AGENT = "${lib.getLib geoclue2-with-demo-agent}/libexec/geoclue-2.0/demos/agent";

  postInstall = ''
    mkdir -p $out/share/{polkit-1/rules.d,cosmic/com.system76.CosmicSettings.Shortcuts/v1}
    cp data/polkit-1/rules.d/*.rules $out/share/polkit-1/rules.d/
    cp data/system_actions.ron $out/share/cosmic/com.system76.CosmicSettings.Shortcuts/v1/system_actions
  '';

  postFixup = ''
    patchelf --add-rpath ${lib.makeLibraryPath [ wayland ]} $out/bin/cosmic-settings-daemon
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-settings-daemon";
    description = "Settings daemon for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-settings-daemon";
  };
}
