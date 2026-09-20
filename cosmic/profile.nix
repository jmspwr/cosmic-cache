{ ... }:
{
  boot.isContainer = true;
  networking.networkmanager.enable = true;
  services = {
    desktopManager.cosmic.enable = true;
    displayManager.cosmic-greeter.enable = true;
    pipewire = {
      enable = true;
      pulse.enable = true;
    };
  };
  system.stateVersion = "25.11";
}
