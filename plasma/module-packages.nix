# These arguments belong only to the Plasma module. Do not feed this scope back
# into the host package fixpoint: doing so rebuilds Gear and apps like EasyEffects.
{ hostPkgs, desktop }:
hostPkgs
// {
  kdePackages =
    hostPkgs.kdePackages
    // desktop
    // {
      # Qt5 integration is a separate variant, not one of the cached Qt6 outputs.
      breeze = desktop.breeze // {
        qt5 = hostPkgs.kdePackages.breeze.qt5;
      };
      plasma-integration = desktop.plasma-integration // {
        qt5 = hostPkgs.kdePackages.plasma-integration.qt5;
      };
    };
}
