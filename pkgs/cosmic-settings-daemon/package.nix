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
  version = "1.10.0-unstable-2026-10-20";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-settings-daemon";
    rev = "655b14fb9572dd7f7231ec6c343c63984e99741a";
    hash = "sha256-icTGIcs9W7KNJE/2ULikbWM7RsMBN11vIeTJCuqgpmw=";
  };

  cargoHash = "sha256-19GGcZmxq/Yp0A6wnR6Y4zKwZ9EiQBj1i5+D9lDAFz8=";

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
