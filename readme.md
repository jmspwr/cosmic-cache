# NixOS COSMIC

Nix package set for using COSMIC as it is developed.

## Usage

### Flakes

If you have an existing `configuration.nix`, you can use the `nixos-cosmic` flake with the following in an adjacent `flake.nix` (e.g. in `/etc/nixos`):

**Note:** If switching from traditional evaluation to flakes, `nix-channel` will no longer have any effect on the nixpkgs your system is built with, and therefore `nixos-rebuild --upgrade` will also no longer have any effect. You will need to use `nix flake update` from your flake directory to update nixpkgs and nixos-cosmic.

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable"; # NOTE: change "nixos-unstable" to "nixos-26.05" for stable channel

    nixos-cosmic.url = "github:lilyinstarlight/nixos-cosmic";
  };

  outputs = { self, nixpkgs, nixos-cosmic }: {
    nixosConfigurations = {
      # NOTE: change "host" to your system's hostname
      host = nixpkgs.lib.nixosSystem {
        modules = [
          nixos-cosmic.nixosModules.default
          ./configuration.nix
        ];
      };
    };
  };
}
```

Enable COSMIC with `services.desktopManager.cosmic.enable = true` and `services.displayManager.cosmic-greeter.enable = true` in your NixOS configuration.

To use COSMIC Store to manage Flatpaks, set `services.flatpak.enable = true` and then run `flatpak remote-add --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo` in your user terminal to add the Flathub repository.


## Build Requirements

This flake doesn't provide binary cache, so local building of cosmic packages is required.

Generally you will need roughly 16 GiB of RAM and 40 GiB of disk space, but it can be built with less RAM by reducing build parallelism, either via `--cores 1` or `-j 1` or both, on `nix build`, `nix-build`, and `nixos-rebuild` commands.


## Troubleshooting

### Phantom non-existent display on Nvidia ([cosmic-randr#13](https://github.com/pop-os/cosmic-randr/issues/13))

If while using an Nvidia GPU, `cosmic-settings` and `cosmic-randr list` show an additional display that can not be disabled, try Nvidia's experimental framebuffer device.

Add to your configuration:

```nix
boot.kernelParams = [ "nvidia_drm.fbdev=1" ];
```

### COSMIC Utilities - Clipboard Manager not working

The zwlr\_data\_control\_manager\_v1 protocol needs to be available. Enable it in cosmic-comp via the following configuration:

```nix
environment.sessionVariables.COSMIC_DATA_CONTROL_ENABLED = 1;
```

### COSMIC Utilities - Observatory not working

The monitord service must be enabled to use Observatory.

```nix
systemd.packages = [ pkgs.observatory ];
systemd.services.monitord.wantedBy = [ "multi-user.target" ];
```
