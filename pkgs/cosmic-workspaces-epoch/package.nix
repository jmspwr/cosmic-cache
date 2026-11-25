{
  lib,
  rustPlatform,
  fetchFromGitHub,
  libcosmicAppHook,
  pkg-config,
  libgbm ? null,
  libinput,
  mesa,
  udev,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-workspaces-epoch";
  version = "1.12.0-unstable-2026-11-24";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-workspaces-epoch";
    rev = "f244ea6da0ce17076579d69a6379071c677f3fa7";
    hash = "sha256-r4ZwWuKYeW8nvZXJYR6ByOVqVVzK04Nhx37U5j28Vz8=";
  };

  cargoHash = "sha256-U/Fl1Hg1fKIXB8wooaMG6dbXauwjzZ7twvGOIraA6BU=";

  nativeBuildInputs = [
    libcosmicAppHook
    pkg-config
  ];
  buildInputs = [
    (if libgbm != null then libgbm else mesa)
    libinput
    udev
  ];

  postInstall = ''
    mkdir -p $out/share/{applications,icons/hicolor/scalable/apps}
    cp data/*.desktop $out/share/applications/
    cp data/*.svg $out/share/icons/hicolor/scalable/apps/
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-workspaces-epoch";
    description = "Workspaces Epoch for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-workspaces";
  };
}
