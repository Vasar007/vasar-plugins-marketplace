# Installing and updating

This page gives the details of the install and the update of the plugins of this marketplace. The short steps are in the [README](../README.md#install). The official page [Install and manage plugins](https://code.claude.com/docs/en/plugins/install) describes everything else.

## Add the marketplace

In a Claude Code session, run this command. The `owner/repo` form is the short form for a GitHub repository.

```text
/plugin marketplace add Vasar007/vasar-plugins-marketplace
```

The full URL works too:

```text
/plugin marketplace add https://github.com/Vasar007/vasar-plugins-marketplace
```

To add the marketplace in a configuration file, use `.claude/settings.local.json`:

```json
{
  "extraKnownMarketplaces": {
    "vasar-plugins-marketplace": {
      "source": {
        "source": "git",
        "url": "https://github.com/Vasar007/vasar-plugins-marketplace"
      }
    }
  }
}
```

## Install one plugin

After you add the marketplace, install a plugin by name:

```text
/plugin install dev-essentials@vasar-plugins-marketplace
/plugin install doc-styles@vasar-plugins-marketplace
/plugin install dotnet-backend-dev@vasar-plugins-marketplace
/plugin install kb@vasar-plugins-marketplace
```

In a session, this command does not install at once. It opens the details of the plugin in the `/plugin` panel. You read what the plugin adds and choose a scope: your user, the project, or only your local copy of the project. The last line of the install summary says whether the plugin is active or needs `/reload-plugins`.

`dotnet-backend-dev` uses skills and agents of `dev-essentials`, so it declares it as a dependency. If you install it, Claude Code also installs `dev-essentials` at the same scope.

In your shell, `claude plugin install <plugin>@vasar-plugins-marketplace` installs at user scope. With Claude Code v2.1.292 or later, this one command adds the marketplace and installs the plugin:

```bash
claude plugin install dev-essentials --marketplace Vasar007/vasar-plugins-marketplace
```

## Enable plugins for a project

To enable specific plugins for a project, extend the same `.claude/settings.local.json` file:

```json
{
  "extraKnownMarketplaces": {
    "vasar-plugins-marketplace": {
      "source": {
        "source": "git",
        "url": "https://github.com/Vasar007/vasar-plugins-marketplace"
      }
    }
  },
  "enabledPlugins": {
    "dev-essentials@vasar-plugins-marketplace": true,
    "dotnet-backend-dev@vasar-plugins-marketplace": true
  }
}
```

After you edit the configuration or install a plugin, run `/reload-plugins`. This loads the changes without a restart. A plugin that a project file enables can still need an install on your machine. The official page [Plugin loading reference](https://code.claude.com/docs/en/plugins/loading#enabled-in-project-settings-but-not-installed) explains this case.

## Update the plugins

A push to `main` does not change the plugins that you installed. Claude Code compares the `version` in the `plugin.json` of a plugin with the version of the installed copy. If the two versions are the same, the installed copy stays. For the rules of a new version, see [Versioning Policy](../CLAUDE.md#versioning-policy).

After a new release, update the plugins in one of these ways:

1. In a session, run `/plugin`, open the "Marketplaces" tab, select `vasar-plugins-marketplace`, and select "Update marketplace". The docs say that this refreshes the listing and updates the plugins that you installed from it.
2. In your shell, run `claude plugin update <plugin>@vasar-plugins-marketplace` for each plugin.

Then run `/reload-plugins` in a running session to load the new versions. If you do not, the next session loads them.

The command `/plugin marketplace update vasar-plugins-marketplace` updates the listing of the marketplace. The docs do not say that this named command also updates the installed plugins. Only the case with no name is clear: in a shell, `claude plugin marketplace update` with no name refreshes every listing and leaves the installed plugins at their versions. So use one of the two ways above to update a plugin.

## Update the plugins automatically

For this marketplace, automatic updates are off by default. To turn them on in a session, run `/plugin`, open the "Marketplaces" tab, select `vasar-plugins-marketplace`, and select "Enable auto-update". To turn them on in the configuration, add `"autoUpdate": true` next to `source` in the `extraKnownMarketplaces` entry of the marketplace:

```json
{
  "extraKnownMarketplaces": {
    "vasar-plugins-marketplace": {
      "source": {
        "source": "git",
        "url": "https://github.com/Vasar007/vasar-plugins-marketplace"
      },
      "autoUpdate": true
    }
  }
}
```

With automatic updates, Claude Code waits a random delay of up to ten minutes after your first message in a session. Then it refreshes the marketplace and updates the plugins on disk. The running session keeps the old versions. To load the new versions, run `/reload-plugins` or start a new session.

The page [Keep plugins updated](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated) gives the details. The page [When auto-update runs](https://code.claude.com/docs/en/plugins/loading#when-auto-update-runs) gives the timing.
