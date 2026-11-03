{
  lib,
  stdenv,
  cargo,
  cmake,
  fetchFromGitHub,
  nix-update-script,
  qt6,
  rustPlatform,
  rustc,
}:

stdenv.mkDerivation (self: {
  pname = "cutecosmic";
  version = "0.2.0-unstable-2026-11-03";

  src = fetchFromGitHub {
    owner = "IgKh";
    repo = "cutecosmic";
    rev = "e83cbd2a51f86c7e441fa3bb3235179c474395b5";
    hash = "sha256-geZufOLINRy5j5Gpa7VupO3QOEk3qJUTaZ/BxKU2TSI=";
  };

  cargoDeps = rustPlatform.fetchCargoVendor {
    inherit (self) src;
    name = self.pname;
    sourceRoot = "${self.src.name}/bindings";
    hash = "sha256-u7WXVH5TqCvbpHDFPAw2bjurIHLmX+LmypCpRHMGcXA=";
  };

  cargoRoot = "bindings";

  nativeBuildInputs = [
    cmake
    qt6.wrapQtAppsHook
    rustPlatform.cargoSetupHook
    cargo
    rustc
  ];

  buildInputs = [
    qt6.qtbase
    qt6.qtdeclarative
  ];

  cmakeFlags = [
    "-DFETCHCONTENT_SOURCE_DIR_CORROSION=${fetchFromGitHub {
      owner = "corrosion-rs";
      repo = "corrosion";
      rev = "v0.5.2";
      hash = "sha256-sO2U0llrDOWYYjnfoRZE+/ofg3kb+ajFmqvaweRvT7c=";
    }}"
  ];

  postPatch = ''
    substituteInPlace platformtheme/CMakeLists.txt \
      --replace-fail "\''${QT_INSTALL_PLUGINS}/platformthemes" \
      "${qt6.qtbase.qtPluginPrefix}/platformthemes"
  '';

  passthru.updateScript = nix-update-script {};

  meta = {
    homepage = "https://github.com/IgKh/cutecosmic";
    description = "Qt platform theme for COSMIC desktop environment";
    license = lib.licenses.gpl3Only;
    platforms = lib.platforms.linux;
  };
})
