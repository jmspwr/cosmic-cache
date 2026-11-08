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
  version = "0.2.0-unstable-2026-11-08";

  src = fetchFromGitHub {
    owner = "IgKh";
    repo = "cutecosmic";
    rev = "707244c52a578d4766205ab4cdb03561cb5b306f";
    hash = "sha256-3/ILsK8PBKjRynZEiGWj6TfvPdXS2UUmnCWo+ZEJdIg=";
  };

  cargoDeps = rustPlatform.fetchCargoVendor {
    inherit (self) src;
    name = self.pname;
    sourceRoot = "${self.src.name}/bindings";
    hash = "sha256-vFShpb87LYOdPR0APgUL0M28nXWN9Gvmf2q45VKwSYA=";
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
