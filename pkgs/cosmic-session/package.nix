{
  lib,
  fetchFromGitHub,
  rustPlatform,
  bash,
  dbus,
  just,
  replaceVars,
  stdenv,
  cutecosmic,
  qt6,
  nix-update-script,
}:

rustPlatform.buildRustPackage {
  pname = "cosmic-session";
  version = "1.8.0-unstable-2026-09-15";

  src = fetchFromGitHub {
    owner = "pop-os";
    repo = "cosmic-session";
    rev = "cd90a03e3fa525a4ff9442fdd341859c3ced2ebb";
    hash = "sha256-23sVeOkS8Ssuz/8Bf7zlawHUWx6uZBqYV64dVkUXB4g=";
  };

  cargoHash = "sha256-IoSLvxpc/1X1a6cDl4ZpoUpxHM7bsH3v2BU6wiQROhM=";

  patches = [
    (replaceVars ./hardcode-cutecosmic-plugin-path.patch {
      cutecosmic = "${cutecosmic}/${qt6.qtbase.qtPluginPrefix}";
    })
  ];

  postPatch = ''
    substituteInPlace data/start-cosmic \
      --replace-fail /usr/bin/cosmic-session "''${!outputBin}/bin/cosmic-session" \
      --replace-fail /usr/bin/dbus-run-session '${lib.getExe' dbus "dbus-run-session"}'
    substituteInPlace data/cosmic.desktop \
      --replace-fail /usr/bin/start-cosmic "''${!outputBin}/bin/start-cosmic"
  '';

  nativeBuildInputs = [ just ];
  buildInputs = [ bash ];

  dontUseJustBuild = true;
  dontUseJustCheck = true;

  justFlags = [
    "--set"
    "prefix"
    (placeholder "out")
    "--set"
    "cargo-target-dir"
    "target/${stdenv.hostPlatform.rust.cargoShortTarget}"
    "--set"
    "cosmic_dconf_profile"
    "${placeholder "out"}/etc/dconf/profile/cosmic"
  ];

  # use `orca` from PATH (instead of absolute path) if available
  env.ORCA = "orca";

  passthru = {
    updateScript = nix-update-script {
      extraArgs = [
        "--version-regex"
        "epoch-(.*)"
      ];
    };
    providedSessions = [ "cosmic" ];
  };

  meta = {
    homepage = "https://github.com/pop-os/cosmic-session";
    description = "Session manager for the COSMIC Desktop Environment";
    license = lib.licenses.gpl3Only;
    mainProgram = "cosmic-session";
    maintainers = with lib.maintainers; [
      # lilyinstarlight
    ];
    platforms = lib.platforms.linux;
  };
}
