pkgs:

{
  cosmic-applibrary = pkgs.lib.warn "`cosmic-applibrary` has been renamed to `cosmic-app-library`." pkgs.cosmic-app-library;
  cosmic-ext-examine = pkgs.lib.warn "`cosmic-ext-examine` has been renamed to `examine`." pkgs.examine;
  cosmic-ext-forecast = pkgs.lib.warn "`cosmic-ext-forecast` has been renamed to `forecast`." pkgs.forecast;
  cosmic-ext-tasks = pkgs.lib.warn "`cosmic-ext-tasks` has been renamed to `tasks`." pkgs.tasks;
}
