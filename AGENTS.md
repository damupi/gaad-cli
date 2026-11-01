# AGENTS.md — gaad-cli

## Project overview

`gaad-cli` is a Python CLI for administering Google Analytics 4 via the Admin API v1beta. It is built with Typer + Rich, uses TDD (pytest), and follows Release Please for versioning.

## Stack

- **CLI framework**: Typer (type-hint driven, built on Click)
- **Output formatting**: Rich (tables, colours)
- **Package manager**: uv (`uv sync`, `uv run pytest`, `uv run gaad`). Dependencies are locked in `uv.lock`; dev dependencies live in the `dev` dependency group
- **Build system**: Hatchling via `pyproject.toml`
- **Testing**: pytest + pytest-mock + pytest-cov (80% coverage minimum enforced)
- **GA4 API**: `google.analytics.admin_v1beta` for most commands; `google.analytics.admin_v1alpha` for `annotations`, `channel-groups`, and `bigquery-links` (no top-level alias)

## Key conventions

### API version
Most commands use `google.analytics.admin_v1beta`. The `annotations`, `channel-groups`, and `bigquery-links` commands use `google.analytics.admin_v1alpha` — these APIs are only available in the alpha client. Never use the top-level `google.analytics.admin` alias.

```python
# v1beta (accounts, properties, data-streams, key-events, custom-dimensions, custom-metrics)
from google.analytics.admin_v1beta import types as admin_types
from google.analytics.admin_v1beta.types import ListPropertiesRequest

# v1alpha (annotations, channel-groups, bigquery-links)
from google.analytics.admin_v1alpha import types as alpha_types
```

### Auth
Credentials are stored in `~/.config/gaad-cli/config.json`. The config dir can be overridden with the `GAAD_CONFIG_DIR` env var (used in tests).

Three auth methods: `service-account`, `oauth2`, `token`. See `src/gaad/auth.py`.

### Command structure
Each command group lives in its own file under `src/gaad/commands/`. Every file follows this pattern:
1. Import shared `get_client()` from `gaad.shared`; pass `"v1alpha"` for alpha-only resources
2. `_*_to_dict(obj)` — converts API response to flat dict (for JSON/CSV)
3. `_render_*(obj, output)` — renders in table/json/csv
4. Command functions decorated with `@*_app.command("name")`

### Output format
All list/get/create/patch commands support `--output table|json|csv` (default: `table`).

### Destructive operations
`delete` and `archive` commands require `--force` to skip confirmation. Without it, they fetch the resource name first and prompt before acting.

`archive` commands always fetch the resource **before** archiving, also with `--force`: GA4 excludes archived custom dimensions and metrics from `get` (it returns 404), so anything needed for the prompt or the success message must be read while the resource is still active. Never call `get_*` on a resource after archiving it.

### Field masks (patch/update)
Always use `google.protobuf.field_mask_pb2.FieldMask(paths=[...])`. Only include paths for fields explicitly provided by the user.

## TDD workflow

For every new command group:
1. Write all tests first (red)
2. Implement until tests pass (green)
3. Run `uv run pytest -q` — full suite must stay ≥80% coverage

Change dependencies only with `uv add` / `uv add --group dev` / `uv lock --upgrade-package <pkg>` so `pyproject.toml` and `uv.lock` stay in sync, and commit both. Dependency upgrades go in their own PR with the full test suite passing. CI (`.github/workflows/tests.yml`) runs `uv run --locked pytest`, so a stale lock fails the build.

Tests patch `gaad.commands.<module>.get_client` for command-level API assertions. Authentication failure tests may patch `gaad.shared.client.get_credentials`. Use the `tmp_config_dir` fixture (sets `GAAD_CONFIG_DIR`) for config isolation.

## Agent skill and agent

```
skills/gaad-cli/                 # Agent skill: SKILL.md + compatibility.json
agents/google-analytics-admin.md # GA4 admin subagent (Claude Code frontmatter)
```

They are product artifacts for users of `gaad`, not configuration for working on this repository, so they live at the top level (not in `.claude/`). Users install them with the agent-agnostic prompt in README.md ("Agent skill and agent"), which must never hard-code an agent's skills or agents path.

- **Keep the skill accurate.** When a change to `src/gaad/` affects commands, options, output or behavior, update `skills/gaad-cli/SKILL.md` in the same PR. The skill must describe the CLI truthfully, including limitations and safety rules.
- **No command reference in the agent.** `agents/google-analytics-admin.md` covers role, workflow, rules, hierarchy, UI links, output format and boundaries; command syntax lives only in the skill.
- **Keep both generic.** No personal names, IDs or organisation-specific values; reference other agents generically (the reporting agent points to github.com/damupi/gafour).
- `skills/gaad-cli/compatibility.json` holds `cli_version`; release-please bumps it with each release (`extra-files`). Do not edit it by hand.

## Git / versioning

Uses [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` new feature
- `fix:` bug fix
- `chore:` maintenance
- `docs:` documentation only

Release Please runs from `.github/workflows/release-please.yml` with its settings in `release-please-config.json` and `.release-please-manifest.json`. On every push to `main` it opens or updates a release PR that bumps `pyproject.toml`, the manifest and `skills/gaad-cli/compatibility.json` and updates `CHANGELOG.md`; merging it creates the `vX.Y.Z` tag and GitHub release. Do not edit versions, the manifest or `CHANGELOG.md` by hand (except fixing published entries in a `chore:` commit).

Always **squash-merge** PRs: the PR title becomes the commit message, so it must be a Conventional Commit. release-please also reads merge commits and conventional lines in commit bodies, which duplicate CHANGELOG entries.

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
| `bigquery-links` | `list`, `get`, `create`, `patch`, `delete` |

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
