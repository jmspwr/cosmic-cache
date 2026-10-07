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
  version = "1.10.0-unstable-2026-09-30";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-sound-theme";
    rev = "bf5335fe1af0cb3bee83e1ad2371410ee434658d";
    hash = "sha256-TVB+GnFmrPf1+OdfQozFoi+P41oNNW+4qrKtVl08Bbg=";
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
