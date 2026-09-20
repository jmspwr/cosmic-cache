# Representative Plasma laptop, used for both package discovery and verification.
{ pkgs, ... }:
{
  imports = [ ./minimal.nix ];
  environment.systemPackages = [ pkgs.easyeffects ];
  boot.isContainer = true;
  hardware.bluetooth.enable = true;
  networking.networkmanager.enable = true;
  powerManagement.enable = true;
  services = {
    colord.enable = true;
    desktopManager.plasma6.enable = true;
    flatpak.enable = true;
    hardware.bolt.enable = true;
    pipewire = {
      enable = true;
      pulse.enable = true;
    };
    printing.enable = true;
  };
  system.stateVersion = "25.11";
}
