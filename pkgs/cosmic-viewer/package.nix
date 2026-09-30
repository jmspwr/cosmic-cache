{
  lib,
  stdenv,
  rustPlatform,
  fetchFromGitHub,
  just,
  cmake,
  nasm,
  libcosmicAppHook,
}:
rustPlatform.buildRustPackage (finalAttrs: {
  pname = "cosmic-viewer";
  version = "1.9.0-unstable-2026-09-30";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-viewer";
    rev = "f3c21b635b10f4d23d4718836ba2ca80ee89d0e7";
    hash = "sha256-czsJGpzQn/frh0h8YyQcQCSNsR237p/ZdR4lr5/C+F4=";
  };

  cargoHash = "sha256-vPUhFkDFIEJ+uHmCcc54jQVzks3orQdu2JUPEfIimOw=";

  separateDebugInfo = true;
  __structuredAttrs = true;

  env.VERGEN_GIT_SHA = finalAttrs.src.rev;

  nativeBuildInputs = [
    just
    cmake
    nasm
    libcosmicAppHook
    rustPlatform.bindgenHook
  ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "cargo-target-dir"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}"
  ];

  meta = {
    description = "Image viewer for the COSMIC Desktop Environment";
    homepage = "https://github.com/pop-os/cosmic-viewer";
    license = lib.licenses.gpl3Only;
    mainProgram = "cosmic-viewer";
    platforms = lib.platforms.linux;
    teams = [ lib.teams.cosmic ];
  };
})
