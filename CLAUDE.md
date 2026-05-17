# CLAUDE.md — gaad-cli

## Project overview

`gaad-cli` is a Python CLI for administering Google Analytics 4 via the Admin API v1beta. It is built with Typer + Rich, uses TDD (pytest), and follows Release Please for versioning.

## Stack

- **CLI framework**: Typer (type-hint driven, built on Click)
- **Output formatting**: Rich (tables, colours)
- **Package manager**: uv (`uv pip install`, `uv run pytest`, `uv run gaad`)
- **Build system**: Hatchling via `pyproject.toml`
- **Testing**: pytest + pytest-mock + pytest-cov (80% coverage minimum enforced)
- **GA4 API**: `google.analytics.admin_v1beta` for most commands; `google.analytics.admin_v1alpha` for `annotations` and `channel-groups` (no top-level alias)

## Key conventions

### API version
Most commands use `google.analytics.admin_v1beta`. The `annotations` and `channel-groups` commands use `google.analytics.admin_v1alpha` — these APIs are only available in the alpha client. Never use the top-level `google.analytics.admin` alias.

```python
# v1beta (accounts, properties, data-streams, key-events, custom-dimensions, custom-metrics)
from google.analytics.admin_v1beta import types as admin_types
from google.analytics.admin_v1beta.types import ListPropertiesRequest

# v1alpha (annotations, channel-groups)
from google.analytics.admin_v1alpha import types as alpha_types
```

### Auth
Credentials are stored in `~/.config/gaad-cli/config.json`. The config dir can be overridden with the `GAAD_CONFIG_DIR` env var (used in tests).

Three auth methods: `service-account`, `oauth2`, `token`. See `src/gaad/auth.py`.

### Command structure
Each command group lives in its own file under `src/gaad/commands/`. Every file follows this pattern:
1. `_get_client()` — loads config, authenticates, returns admin client
2. `_*_to_dict(obj)` — converts API response to flat dict (for JSON/CSV)
3. `_render_*(obj, output)` — renders in table/json/csv
4. Command functions decorated with `@*_app.command("name")`

### Output format
All list/get/create/patch commands support `--output table|json|csv` (default: `table`).

### Destructive operations
`delete` and `archive` commands require `--force` to skip confirmation. Without it, they fetch the resource name first and prompt before acting.

### Field masks (patch/update)
Always use `google.protobuf.field_mask_pb2.FieldMask(paths=[...])`. Only include paths for fields explicitly provided by the user.

## TDD workflow

For every new command group:
1. Write all tests first (red)
2. Implement until tests pass (green)
3. Run `uv run pytest -q` — full suite must stay ≥80% coverage

Test patches target `gaad.commands.<module>.get_credentials` and `gaad.commands.<module>.build_admin_client`. Use `tmp_config_dir` fixture (sets `GAAD_CONFIG_DIR`) for config isolation.

## Git / versioning

Uses [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` new feature
- `fix:` bug fix
- `chore:` maintenance
- `docs:` documentation only

Release Please is configured in `.github/workflows/release-please.yml` and will auto-create CHANGELOG entries and GitHub releases on merge to `main`.

## Commands available (Phase 1)

| Group | Methods |
|---|---|
| `auth` | `login`, `status`, `logout` |
| `accounts` | `list`, `get`, `get-data-sharing-settings`, `patch`, `delete` |
| `properties` | `list`, `get`, `create`, `patch`, `delete`, `get-data-retention-settings`, `update-data-retention-settings` |
| `data-streams` | `list`, `get`, `create`, `patch`, `delete` |
| `key-events` | `list`, `get`, `create`, `patch`, `delete` |
| `custom-dimensions` | `list`, `get`, `create`, `patch`, `archive` |
| `custom-metrics` | `list`, `get`, `create`, `patch`, `archive` |
| `annotations` | `list`, `get`, `create`, `patch`, `delete` |
| `channel-groups` | `list`, `get`, `create`, `patch`, `delete` |

## Implementation notes

### Channel Groups — valid filter field names

The GA4 API uses internal dimension names that differ from the official docs:

| UI Label | `fieldName` value |
|---|---|
| Default channel group | `eachScopeDefaultChannelGroup` |
| Source | `eachScopeSource` |
| Medium | `eachScopeMedium` |
| Source platform | `eachScopeSourcePlatform` |
| Campaign ID | `eachScopeCampaignId` |
| Campaign name | `eachScopeCampaignName` |
