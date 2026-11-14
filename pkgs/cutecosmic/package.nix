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
  version = "0.2.0-unstable-2026-11-14";

  src = fetchFromGitHub {
    owner = "IgKh";
    repo = "cutecosmic";
    rev = "ba3fba8212857012fcca703f7d16dacc74d8df6f";
    hash = "sha256-WND/pQ9YMnOk8LQDcZz+Ddj7Our3QBFVD3xr1bWPNzo=";
  };

  cargoDeps = rustPlatform.fetchCargoVendor {
    inherit (self) src;
    name = self.pname;
    sourceRoot = "${self.src.name}/bindings";
    hash = "sha256-z78QmKssnhEE7eZksfXgGSe2lIjzY2lCJrUARWdAtro=";
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
    substituteInPlace CMakeLists.txt \
      --replace-fail "\''${QT_INSTALL_LIBS}/cutecosmic" \
      "${builtins.placeholder "out"}/lib"
  '';

  passthru.updateScript = nix-update-script {};

  meta = {
    homepage = "https://github.com/IgKh/cutecosmic";
    description = "Qt platform theme for COSMIC desktop environment";
    license = lib.licenses.gpl3Only;
    platforms = lib.platforms.linux;
  };
})
