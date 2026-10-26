# gaad-cli

A command-line tool for administering Google Analytics 4 (GA4) properties via the Admin API v1beta and v1alpha.

## Installation

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/davidmuleropino/gaad-cli.git
cd gaad-cli
uv venv
uv pip install -e ".[dev]"
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

## Development

```bash
# Run tests
uv run pytest

# Run a specific test file
uv run pytest tests/commands/test_accounts.py -v

# Run the CLI locally
uv run gaad --help
```

## Versioning

This project uses [Release Please](https://github.com/googleapis/release-please) with [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` → minor version bump
- `fix:` → patch version bump
- `feat!:` / `BREAKING CHANGE:` → major version bump

## License

MIT
