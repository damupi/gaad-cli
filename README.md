# gaad-cli

A command-line tool for administering Google Analytics 4 (GA4) properties via the Admin API v1beta and v1alpha.

## Installation

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

Install a release as a standalone tool (recommended). Pick a `vX.Y.Z` tag from the [releases](https://github.com/damupi/gaad-cli/releases):

```bash
uv tool install git+https://github.com/damupi/gaad-cli@vX.Y.Z
uv tool install --force git+https://github.com/damupi/gaad-cli@vX.Y.Z   # upgrade
gaad --version
```

To track the latest `main` instead of a release, omit `@vX.Y.Z`.

For development, clone the repository and create the environment from `uv.lock`:

```bash
git clone https://github.com/damupi/gaad-cli.git
cd gaad-cli
uv sync          # .venv with runtime + dev dependencies (dev dependency group)
```

## Updates

Once a day, `gaad` checks GitHub for a newer release (`vX.Y.Z` tag) and prints a notice on stderr after the command, for example:

```text
A new release of gaad is available: 0.2.0 → 0.3.0
To upgrade, run: uv tool install --force git+https://github.com/damupi/gaad-cli@v0.3.0
Release notes: https://github.com/damupi/gaad-cli/releases/tag/v0.3.0
```

- The suggested command matches how `gaad` is installed: `uv tool install --force …`, `pip install --upgrade "…"`, or `git -C <checkout> pull` for an editable install.
- The check runs `git ls-remote` over HTTPS against this public repository. It never prompts and fails silently when offline.
- It only runs in interactive terminals: not when stderr is redirected (agents, scripts, `--output json` pipelines) and not when `CI` is set. The result is cached for 24 h in `update-check.json` next to the config file (respects `GAAD_CONFIG_DIR`).
- Disable it with `GAAD_NO_UPDATE_CHECK=1`.

```bash
gaad version          # installed version, latest release, and upgrade command
gaad version --json   # machine-readable
gaad --version        # installed version only
```

## Authentication

### Service Account (recommended for automation)

```bash
gaad auth login --method service-account --key-file /path/to/service_account.json
```

The key file is copied to `~/.config/gaad-cli/service_account.json`.

### OAuth2 (recommended for interactive use)

```bash
gaad auth login --method oauth2 --client-secrets /path/to/client_secret.json
```

Opens a browser for Google account authorisation. Token is stored at `~/.config/gaad-cli/`.

### Access Token

```bash
gaad auth login --method token --token YOUR_TOKEN
# or via environment variable
export GA4_ACCESS_TOKEN=YOUR_TOKEN
```

### Check status / logout

```bash
gaad auth status
gaad auth logout
```

## Commands

All commands support `--output table|json|csv` (default: `table`).

### Accounts

```bash
gaad accounts list
gaad accounts get --account-id ID
gaad accounts get-data-sharing-settings --account-id ID
gaad accounts patch --account-id ID --display-name NAME [--region-code CODE]
gaad accounts delete --account-id ID [--force]
```

### Properties

```bash
gaad properties list --account-id ID          # standard properties
gaad properties list --property-id ID         # subproperties of a rollup
gaad properties get --property-id ID
gaad properties create --account-id ID --display-name NAME --time-zone TZ [--currency-code CODE] [--industry-category CAT] [--property-type TYPE]
gaad properties patch --property-id ID [--display-name NAME] [--time-zone TZ] [--currency-code CODE] [--industry-category CAT]
gaad properties delete --property-id ID [--force]
gaad properties get-data-retention-settings --property-id ID
gaad properties update-data-retention-settings --property-id ID [--event-data-retention DURATION] [--user-data-retention DURATION] [--reset-user-data/--no-reset-user-data]
```

### Data Streams

```bash
gaad data-streams list --property-id ID
gaad data-streams get --property-id ID --stream-id ID
gaad data-streams create --property-id ID --display-name NAME --type WEB_DATA_STREAM [--default-uri URL]
gaad data-streams create --property-id ID --display-name NAME --type ANDROID_APP_DATA_STREAM --package-name com.example.app
gaad data-streams create --property-id ID --display-name NAME --type IOS_APP_DATA_STREAM --bundle-id com.example.app
gaad data-streams patch --property-id ID --stream-id ID [--display-name NAME] [--default-uri URL]
gaad data-streams delete --property-id ID --stream-id ID [--force]
```

### Key Events

```bash
gaad key-events list --property-id ID
gaad key-events get --property-id ID --key-event-id ID
gaad key-events create --property-id ID --event-name NAME --counting-method ONCE_PER_EVENT|ONCE_PER_SESSION [--default-numeric-value FLOAT --default-currency-code CODE]
gaad key-events patch --property-id ID --key-event-id ID [--counting-method METHOD] [--default-numeric-value FLOAT --default-currency-code CODE]
gaad key-events delete --property-id ID --key-event-id ID [--force]
```

### Custom Dimensions

```bash
gaad custom-dimensions list --property-id ID
gaad custom-dimensions get --property-id ID --dimension-id ID
gaad custom-dimensions create --property-id ID --parameter-name NAME --display-name NAME --scope EVENT|USER|ITEM [--description TEXT]
gaad custom-dimensions patch --property-id ID --dimension-id ID [--display-name NAME] [--description TEXT] [--disallow-ads-personalization/--no-disallow-ads-personalization]
gaad custom-dimensions archive --property-id ID --dimension-id ID [--force]
```

### Custom Metrics

```bash
gaad custom-metrics list --property-id ID
gaad custom-metrics get --property-id ID --metric-id ID
gaad custom-metrics create --property-id ID --parameter-name NAME --display-name NAME --measurement-unit STANDARD|CURRENCY|... [--restricted-metric-type COST_DATA|REVENUE_DATA]
gaad custom-metrics patch --property-id ID --metric-id ID [--display-name NAME] [--description TEXT] [--measurement-unit UNIT] [--restricted-metric-type TYPE]
gaad custom-metrics archive --property-id ID --metric-id ID [--force]
```

### Annotations

> Uses GA4 Admin API **v1alpha**. System-generated annotations cannot be patched or deleted.

```bash
gaad annotations list --property ID
gaad annotations get ANNOTATION_ID --property ID
gaad annotations create --property ID --title TITLE --color PURPLE|BROWN|BLUE|GREEN|RED|CYAN \
  [--description TEXT] \
  (--date YYYY-MM-DD | --start-date YYYY-MM-DD --end-date YYYY-MM-DD)
gaad annotations patch ANNOTATION_ID --property ID \
  [--title TITLE] [--color COLOR] [--description TEXT] \
  [--date YYYY-MM-DD | --start-date YYYY-MM-DD --end-date YYYY-MM-DD]
gaad annotations delete ANNOTATION_ID --property ID [--force]
```

### Channel Groups

> Uses GA4 Admin API **v1alpha**. System-defined channel groups cannot be patched or deleted.

```bash
gaad channel-groups list --property ID
gaad channel-groups get CHANNEL_GROUP_ID --property ID
gaad channel-groups create --property ID --display-name NAME --rules-json JSON \
  [--description TEXT] [--primary|--no-primary]
gaad channel-groups patch CHANNEL_GROUP_ID --property ID \
  [--display-name NAME] [--description TEXT] [--primary|--no-primary] [--rules-json JSON]
gaad channel-groups delete CHANNEL_GROUP_ID --property ID [--force]
```

`--rules-json` is a JSON array of grouping rules. Each rule requires a `display_name` and an `expression` following the `and_group → or_group → filter` nesting. Valid `fieldName` values: `eachScopeSource`, `eachScopeMedium`, `eachScopeDefaultChannelGroup`, `eachScopeSourcePlatform`, `eachScopeCampaignId`, `eachScopeCampaignName`. Run `gaad channel-groups create --help` for a full example.

### BigQuery Links

> Uses GA4 Admin API **v1alpha**. Creating, updating, and deleting links requires the `analytics.edit` scope plus access to the GA4 property and Google Cloud project.

```bash
gaad bigquery-links list --property-id PROPERTY_ID
gaad bigquery-links get --property-id PROPERTY_ID --link-id LINK_ID

gaad bigquery-links create --property-id PROPERTY_ID \
  --project PROJECT_ID_OR_NUMBER \
  --dataset-location US \
  [--daily-export/--no-daily-export] \
  [--streaming-export/--no-streaming-export] \
  [--fresh-daily-export/--no-fresh-daily-export] \
  [--include-advertising-id/--no-include-advertising-id] \
  [--export-stream DATA_STREAM_ID]... \
  [--exclude-event EVENT_NAME]...

gaad bigquery-links patch --property-id PROPERTY_ID --link-id LINK_ID \
  [--daily-export/--no-daily-export] \
  [--streaming-export/--no-streaming-export] \
  [--fresh-daily-export/--no-fresh-daily-export] \
  [--include-advertising-id/--no-include-advertising-id] \
  [--export-stream DATA_STREAM_ID]... [--clear-export-streams] \
  [--exclude-event EVENT_NAME]... [--clear-excluded-events]

gaad bigquery-links delete --property-id PROPERTY_ID --link-id LINK_ID [--force]
```

Property IDs may be supplied as `123` or `properties/123`. Link and data-stream options accept either bare IDs or full resource names, and projects accept a project ID, project number, or `projects/...` name. `--property` is also accepted as an alias for `--property-id`.

Create defaults all optional export flags to disabled. On patch, paired negative flags explicitly set booleans to false. Repeated `--export-stream` and `--exclude-event` options replace the complete corresponding list; use `--clear-export-streams` or `--clear-excluded-events` to set a list to empty. `project` and `dataset_location` are immutable after creation.

Use `--output table|json|csv` with `list`, `get`, `create`, and `patch`. JSON repeated fields are arrays; CSV stores them as JSON arrays inside their cells. Deletion is permanent and prompts for confirmation unless `--force` is supplied. Standard GA4 properties generally support only one BigQuery link.

## Agent skill and agent

The repository ships two things for coding agents:

- `skills/gaad-cli/` — a skill (`SKILL.md`, `compatibility.json`) with the command reference, limitations and safety rules for `gaad`.
- `agents/google-analytics-admin.md` — a GA4 administration subagent that uses the skill. Its frontmatter follows Claude Code's subagent format; other agents may need to convert it.

Each agent (Claude Code, Codex, pi, Hermes, …) loads skills and subagents from its own location, so installation is agent-agnostic: paste this prompt into the agent you want to equip. Run it again after upgrading `gaad`.

```text
Install or update the gaad-cli agent skill (and, if you support subagents, the
google-analytics-admin agent) for yourself, the agent reading this.

1. Find out where YOU load skills from and, if you support them, where you load subagents /
   custom agents from. Use your own documentation, configuration or conventions. Every agent
   uses different locations, so do not reuse a path from another agent and do not guess.
   Prefer your user-level (global) locations unless I ask for project-level ones. If you
   cannot determine them, ask me.
2. Get the installed gaad version: run `gaad --version` (it prints `gaad X.Y.Z`). If gaad is
   not installed, stop and tell me.
3. Get the files that match that version:
   - If gaad runs from a local checkout of github.com/damupi/gaad-cli (editable install), use
     that checkout.
   - Otherwise clone the matching release tag into a temporary directory:
     `git clone --quiet --depth 1 --branch vX.Y.Z https://github.com/damupi/gaad-cli.git <tmp>`
   The skill is `skills/gaad-cli/` (`SKILL.md`, `compatibility.json`); the agent is
   `agents/google-analytics-admin.md`.
4. Compare with what is already installed. If everything is identical, tell me it is up to
   date and stop.
5. Show me the destination paths and a summary of what will be added, changed or removed, and
   wait for my approval.
6. Install:
   - Copy the whole `gaad-cli` skill directory to `<your skills location>/gaad-cli/`, replacing
     the previous files and removing files that no longer exist in the source.
   - If you support subagents, copy `google-analytics-admin.md` to your agents location. If
     your agent format needs different frontmatter, convert only the frontmatter (name,
     description, tools, preloaded skills) and keep the body unchanged; tell me what you
     converted. If you do not support subagents, skip it.
   - Do not edit the content otherwise. If a location or an existing installed directory is a
     symbolic link, keep the link and update the files in its resolved target.
7. Delete the temporary clone, if any. Tell me whether you need a restart or reload to pick up
   the changes.
```

`compatibility.json` records the CLI version the skill was reviewed for (`cli_version`); release-please updates it with every release. The skill tells the agent to suggest this prompt when that version differs from `gaad --version`.

## Development

Dependencies are locked in `uv.lock`. `uv sync` and `uv run` use it; CI runs `uv run --locked pytest`.

```bash
# Run tests
uv run pytest

# Run a specific test file
uv run pytest tests/commands/test_accounts.py -v

# Run the CLI locally
uv run gaad --help

# Add or upgrade dependencies (updates pyproject.toml and uv.lock; commit both)
uv add <package>
uv add --group dev <package>
uv lock --upgrade-package <package>   # or: uv lock --upgrade
```

## Versioning

This project uses [Release Please](https://github.com/googleapis/release-please) with [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` → minor version bump
- `fix:` → patch version bump
- `feat!:` / `BREAKING CHANGE:` → major version bump

Merge pull requests with **Squash and merge** (the repository only allows squash merges). release-please also reads merge commits, which would duplicate CHANGELOG entries.

## License

MIT
