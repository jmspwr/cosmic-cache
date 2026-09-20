{ lib, pkgs, ... }:
{
  # Desktop controls stay available; everyday applications belong to COSMIC.
  environment.plasma6.excludePackages = lib.mkDefault (
    with pkgs.kdePackages;
    [
      ark
      discover
      dolphin
      dolphin-plugins
      elisa
      gwenview
      kate
      khelpcenter
      konsole
      okular
      plasma-browser-integration
      qrca
      spectacle
    ]
  );
}
