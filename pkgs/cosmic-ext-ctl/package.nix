{
  lib,
  fetchFromGitHub,
  rustPlatform,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-ext-ctl";
  version = "1.5.0-unstable-2026-10-14";

  src = fetchFromGitHub {
    owner = "cosmic-utils";
    repo = "cosmic-ctl";
    rev = "0efbe3dc669bcd23d6814ed28671e363d7690441";
    hash = "sha256-Z7xuEsw8X2BVp+86fPDyEnAinUotQxWi4yMeHwICYz4=";
  };

  cargoHash = "sha256-XKqylax1O1i3ldJDG/RuAblaMWngJQW5UPS91G2R4KA=";

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI for COSMIC Desktop Environment configuration management";
    homepage = "https://github.com/cosmic-utils/cosmic-ctl";
    license = lib.licenses.gpl3Only;
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
    mainProgram = "cosmic-ctl";
  };
}
