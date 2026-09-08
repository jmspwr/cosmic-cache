# COSMIC binary cache builder

Prepared 8 September 2026. Source-inspected starter; not yet deployed or Nix-build-tested.

This is a dedicated public builder repository, not a copy of a personal NixOS configuration.
It follows `amozeo/nixos-cosmic/main`, whose recipes contain maintainer-updated COSMIC Git snapshots.
It does not claim to package every instantaneous upstream HEAD.

## Architecture

GitHub Actions resolves one upstream revision, builds the x86_64 COSMIC desktop packages on separate
standard Linux runners, and uploads their runtime closures to a public Cachix cache. It does not upload
an entire NixOS system, personal configuration, proprietary apps, authentication files or build secrets.
The per-cache Cachix write token is available only to upload/retention steps, not desktop compilation.
There are no pull-request-triggered privileged builds.

A fresh final runner must obtain every selected output with local compilation disabled and no remote
builders. The primary COSMIC derivations must not set `preferLocalBuild`. A NixOS module evaluation then
checks that the module selects identical output paths. Only after these checks and Cachix retention
succeed is the `cached` branch advanced. This verifies substitution at that moment, not GUI correctness
on a particular laptop or permanent future availability of the provider.

The module imports matching NixOS integration modules from the upstream recipe set and supplies its
already-instantiated package outputs. It does not rebuild that package set against the user's channel.
This adds a separate Nixpkgs dependency set for COSMIC, not a replacement for the whole system's channel.
The existing `services.desktopManager.cosmic.enable` and `services.displayManager.cosmic-greeter.enable`
declarations remain in the user's configuration.

## Activation after the first successful publication

Only after the `cached` branch exists and the workflow has succeeded, add this to the existing imports:

```nix
((fetchTarball "https://github.com/jmspwr/cosmic-cache/archive/refs/heads/cached.tar.gz") + "/default.nix")
```

The module also supplies the cache URL and public signing keys. No local `flake.nix` or `flake.lock` is
created. The configuration still needs its existing `flakes` experimental feature because the module
consumes an upstream flake. Evaluation remains non-flake/impure, as in the current NixOS workflow.

The `cached` branch rolls automatically after completed builds. `snapshot.json` records the exact
revision that was built; upstream's dependency lock is intentionally retained. This is build provenance,
not a user-managed freeze of the moving cached channel.

Use the existing root-channel-based rebuild procedure; make the Cachix URL and public key available
through command-line Nix options during the first rebuild, before the persistent cache settings are
active. Do not enable the source-only `amozeo/nixos-cosmic` import as well.

For a strict no-source-build requirement on every update, preflight the exact evaluated COSMIC package
paths before activation and abort on cache misses. Do not globally set `max-jobs=0` for the full NixOS
system: normal configuration assembly still requires local derivations. The module alone does not
prevent Nix's normal source-build fallback if a provider later loses a published binary.

## Resource and spending limits

Only standard `ubuntu-24.04` GitHub-hosted runners are selected, and the workflow is gated to public
repositories. No paid runner, subscription, trial or billing change is created. The script cannot verify
account-specific billing overrides; the public-repository/standard-runner constraints must be preserved.

Cachix currently advertises a free 5 GB allowance for open-source projects. It stores compressed data and
normally omits dependencies already in cache.nixos.org. This has not yet been measured for this package
set. Whole-desktop coverage within 5 GB is not guaranteed. Standard GitHub Linux runners also have finite
disk, memory and job time: a component can fail to build within those limits. Failure leaves the last
published branch unchanged; there is no automatic paid escalation or laptop compilation.

Only runtime closures are pushed. A named Cachix retention root protects the two latest completed
snapshots; older remote cache entries become eligible for Cachix's own storage management. This does
not delete any local files, NixOS generations or local Nix store entries. No local garbage-collection,
pruning or deletion commands are included.

The first build is genuinely a build on GitHub, not a previously verified cache hit. Automatic daily
runs start only after installation. A schedule is not a promise of a successful fresh package every day;
upstream recipes, quota, runner resource failures and GitHub inactivity policies can interrupt it.

## Setup

Use the accompanying self-contained `setup-cosmic-cache.py` from a terminal with `git`, `gh` and Python.
It requires the `jmspwr` GitHub account and only creates/updates the dedicated `jmspwr/cosmic-cache`
repository. Existing unrelated repositories are not used. The repository is public and contains only
these builder files and public cache metadata.

The unavoidable account step is to log in to Cachix and create a free PUBLIC cache named
`jmspwr-cosmic` (or pass another name with `--cache`), with Cachix-managed signing. Generate a per-cache
write token, not an account-wide personal token. Enter it only into the local GitHub CLI secret prompt;
never into ChatGPT, a shell command argument or a tracked file. GitHub CLI encrypts it before upload.

The setup script can request a one-time GitHub CLI browser login, because the ChatGPT GitHub connection
is not a transferable terminal credential. The script does not modify `/etc/nixos`, rebuild NixOS,
install COSMIC locally or reboot.

## Validation status

Python syntax and offline helper/publication tests were run on the prepared files. This environment had
neither Nix nor Fish and no direct network access, so no Nix evaluation, actual remote build, real Cachix
upload, desktop test, cache sizing measurement or account provisioning has been completed here.

## Primary references

- https://docs.cachix.org/getting-started
- https://docs.cachix.org/continuous-integration-setup/github-actions
- https://docs.cachix.org/pushing
- https://docs.cachix.org/pins
- https://www.cachix.org/pricing
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://cli.github.com/manual/gh_repo_create
- https://cli.github.com/manual/gh_secret_set
- https://github.com/amozeo/nixos-cosmic
