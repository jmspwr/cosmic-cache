{
  lib,
  stdenv,
  meson,
  ninja,
  fetchFromGitHub,
  nix-update-script,
}:

stdenv.mkDerivation (self: {
  pname = "cosmic-sound-theme";
  version = "1.7.0-unstable-2026-07-01";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-sound-theme";
    rev = "7aabe449093787163c74c25aa1bd4663fb4c324c";
    hash = "sha256-hFWTn73SutdOZGbhkcsBR1TNabB+IOrxRndwXaikqN8=";
  };

  nativeBuildInputs = [
    meson
    ninja
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "epoch-(.*)"
    ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-sound-theme";
    description = "System76 COSMIC Sound Theme";
    license = lib.licenses.cc-by-sa-40;
  };
})
