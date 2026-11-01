---
name: gaad-cli
description: Administers Google Analytics 4 (GA4) resources via the gaad CLI (Admin API v1beta and v1alpha). Use when the user asks to list, create, update, or delete GA4 accounts, properties, subproperties, data streams, key events, custom dimensions, custom metrics, annotations, channel groups, or GA4-to-BigQuery links. Also use for gaad authentication and any gaad command. Use a BigQuery/SQL analysis skill instead when the request is to query exported GA4 event data.
---

# gaad-cli

GA4 Admin API v1beta/v1alpha CLI. Config stored at `~/.config/gaad-cli/config.json` (override the directory with `GAAD_CONFIG_DIR`). Every command documents itself with `--help`; treat it as the source of truth for syntax.

## Auth check (always first)

```bash
gaad auth status
```

If not authenticated, run one of:

```bash
# Service account (recommended for automation)
gaad auth login --method service-account --key-file /path/to/service_account.json

# OAuth2 (interactive)
gaad auth login --method oauth2 --client-secrets /path/to/client_secret.json

# Short-lived access token
gaad auth login --method token --token YOUR_TOKEN
# or: export GA4_ACCESS_TOKEN=YOUR_TOKEN

gaad auth logout
```

## Common options

- `--output table|json|csv` (`-o`, default `table`) on `list`, `get`, `create` and `patch` commands. Prefer `--output json` when you parse the result.
- `--force` on `delete` and `archive` skips the confirmation prompt. Without it, the command shows the resource and asks first. Only use `--force` after the user approved that exact change.

## Safety

Read commands are safe. Before any create, patch, delete or archive, show the target (account/property/resource IDs) and the exact change, and get approval. Deleting accounts, properties, data streams, key events, annotations, channel groups and BigQuery links is permanent.

---

## Accounts

```bash
gaad accounts list
gaad accounts get --account-id ID
gaad accounts get-data-sharing-settings --account-id ID
gaad accounts patch --account-id ID --display-name NAME [--region-code CODE]
gaad accounts delete --account-id ID [--force]
```

The numeric account ID is the trailing segment of `name` (e.g. `accounts/123456` → `123456`).

---

## Properties

**Standard properties** (under an account):

```bash
gaad properties list --account-id ACCOUNT_ID
```

**Subproperties** (under a rollup property):

```bash
gaad properties list --property-id ROLLUP_PROPERTY_ID
```

`--account-id` and `--property-id` are mutually exclusive. Use `--property-id` specifically to discover subproperties of a rollup.

Other property commands:

```bash
gaad properties get --property-id ID
gaad properties create --account-id ID --display-name NAME --time-zone TZ \
  [--currency-code CODE] [--industry-category CAT] [--property-type TYPE]
gaad properties patch --property-id ID [--display-name NAME] [--time-zone TZ] \
  [--currency-code CODE] [--industry-category CAT]
gaad properties delete --property-id ID [--force]
gaad properties get-data-retention-settings --property-id ID
gaad properties update-data-retention-settings --property-id ID \
  [--event-data-retention DURATION] [--user-data-retention DURATION] \
  [--reset-user-data/--no-reset-user-data]
```

---

## Data Streams

```bash
gaad data-streams list --property-id ID
gaad data-streams get --property-id ID --stream-id ID
gaad data-streams create --property-id ID --display-name NAME --type WEB_DATA_STREAM \
  [--default-uri URL]
gaad data-streams create --property-id ID --display-name NAME --type ANDROID_APP_DATA_STREAM \
  --package-name com.example.app
gaad data-streams create --property-id ID --display-name NAME --type IOS_APP_DATA_STREAM \
  --bundle-id com.example.app
gaad data-streams patch --property-id ID --stream-id ID [--display-name NAME] [--default-uri URL]
gaad data-streams delete --property-id ID --stream-id ID [--force]
```

---

## Key Events

```bash
gaad key-events list --property-id ID
gaad key-events get --property-id ID --key-event-id ID
gaad key-events create --property-id ID --event-name NAME \
  --counting-method ONCE_PER_EVENT|ONCE_PER_SESSION \
  [--default-numeric-value FLOAT --default-currency-code CODE]
gaad key-events patch --property-id ID --key-event-id ID \
  [--counting-method METHOD] [--default-numeric-value FLOAT --default-currency-code CODE]
gaad key-events delete --property-id ID --key-event-id ID [--force]
```

---

## Custom Dimensions

> Custom definitions are **archived**, not deleted. Archiving keeps historical data but **cannot be undone**: an archived definition cannot be restored, only recreated with the same parameter name.

```bash
gaad custom-dimensions list --property-id ID
gaad custom-dimensions get --property-id ID --dimension-id ID
gaad custom-dimensions create --property-id ID --parameter-name NAME --display-name NAME \
  --scope EVENT|USER|ITEM [--description TEXT]
gaad custom-dimensions patch --property-id ID --dimension-id ID \
  [--display-name NAME] [--description TEXT] \
  [--disallow-ads-personalization/--no-disallow-ads-personalization]
gaad custom-dimensions archive --property-id ID --dimension-id ID [--force]
```

---

## Custom Metrics

> Custom definitions are **archived**, not deleted. Archiving keeps historical data but **cannot be undone**: an archived definition cannot be restored, only recreated with the same parameter name.

```bash
gaad custom-metrics list --property-id ID
gaad custom-metrics get --property-id ID --metric-id ID
gaad custom-metrics create --property-id ID --parameter-name NAME --display-name NAME \
  --measurement-unit STANDARD|CURRENCY|FEET|METERS|KILOMETERS|MILES|MILLISECONDS|SECONDS|MINUTES|HOURS \
  [--restricted-metric-type COST_DATA|REVENUE_DATA]
gaad custom-metrics patch --property-id ID --metric-id ID \
  [--display-name NAME] [--description TEXT] \
  [--measurement-unit UNIT] [--restricted-metric-type TYPE]
gaad custom-metrics archive --property-id ID --metric-id ID [--force]
```

`--restricted-metric-type` is only valid when `--measurement-unit CURRENCY`.

---

## Annotations

Reporting data annotations (Admin API **v1alpha**). These commands take `--property` and a positional annotation ID. System-generated annotations cannot be patched or deleted.

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

---

## Channel Groups

Custom channel groups (Admin API **v1alpha**). These commands take `--property` and a positional channel group ID. System-defined channel groups cannot be patched or deleted.

```bash
gaad channel-groups list --property ID
gaad channel-groups get CHANNEL_GROUP_ID --property ID
gaad channel-groups create --property ID --display-name NAME --rules-json JSON \
  [--description TEXT] [--primary|--no-primary]
gaad channel-groups patch CHANNEL_GROUP_ID --property ID \
  [--display-name NAME] [--description TEXT] [--primary|--no-primary] [--rules-json JSON]
gaad channel-groups delete CHANNEL_GROUP_ID --property ID [--force]
```

`--rules-json` is a JSON array of grouping rules; on `patch` it replaces all existing rules. Each rule needs a `display_name` and an `expression` nested as `and_group → or_group → filter`. Valid `fieldName` values: `eachScopeSource`, `eachScopeMedium`, `eachScopeDefaultChannelGroup`, `eachScopeSourcePlatform`, `eachScopeCampaignId`, `eachScopeCampaignName`. `gaad channel-groups create --help` shows a full example.

---

## BigQuery Links

Use this command group to administer the **GA4-to-BigQuery configuration link**. It does not query or analyse the exported BigQuery event tables; use a BigQuery/GA4 SQL skill for that.

The resource uses Admin API **v1alpha**. Write operations require the `analytics.edit` scope and sufficient access to both the GA4 property and Google Cloud project.

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

Identifier forms:

- Property: `123` or `properties/123` (`--property` is an alias for `--property-id`).
- Link: bare link ID or `properties/123/bigQueryLinks/LINK_ID`.
- Project: project ID, project number, or `projects/PROJECT`.
- Export stream: bare stream ID or `properties/123/dataStreams/STREAM_ID`.

Create defaults optional booleans to false. On patch, negative flags explicitly set a value to false. Repeated stream/event options replace the full list; use the corresponding `--clear-*` option for an empty list. `project` and `dataset_location` are immutable. Deletion is permanent and requires confirmation unless `--force` is used. Standard properties generally allow one BigQuery link.

Use `--output table|json|csv` on `list`, `get`, `create`, and `patch`.

---

## Version and updates

```bash
gaad version          # installed version, latest release, upgrade command
gaad version --json
gaad --version        # installed version only
```

`gaad` prints a new-release notice on stderr only in interactive terminals, so agents normally do not see it; run `gaad version` to check. When an update is available, report the version and the suggested upgrade command to the user. Do not run the upgrade without explicit approval.

This skill was reviewed for the gaad version in `cli_version` of its `compatibility.json`. If that differs from `installed` in `gaad version --json` (or `gaad --version`), tell the user the skill may be outdated and suggest updating it with the "Agent skill and agent" prompt in the gaad-cli README.
