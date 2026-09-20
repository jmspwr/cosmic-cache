{ ... }:
{
  boot.isContainer = true;
  networking.networkmanager.enable = true;
  powerManagement.enable = true;
  services = {
    xserver.desktopManager.lxqt.enable = true;
    flatpak.enable = true;
    pipewire = {
      enable = true;
      pulse.enable = true;
    };
    printing.enable = true;
  };
  system.stateVersion = "25.11";
}
