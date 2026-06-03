#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  DATAVERSE_TEST_QUEUE_ITEM_GUID=<guid> scripts/feature_002_demo.sh
  FEATURE_002_ENABLE_WRITE=1 \
  FEATURE_002_TEST_RECORD_CONFIRMED=<same-guid> \
  FEATURE_002_PREDEMO_STATE_CAPTURED=<same-guid> \
  DATAVERSE_TEST_QUEUE_ITEM_GUID=<guid> scripts/feature_002_demo.sh

Default mode performs preflight checks and the Feature 002 dry-run rehearsal.
Write-enabled mode always runs dry-run first, then requires the explicit
confirmation environment variables above before it can mutate Dataverse.

Optional overrides:
  FEATURE_002_TRANSPORT_FIXTURE
  FEATURE_002_CONVERSATION_FIXTURE
  FEATURE_002_SLICE2_CONFIG
  FEATURE_002_SLICE1_CONFIG
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
cd "$repo_root"

queue_item_id="${DATAVERSE_TEST_QUEUE_ITEM_GUID:-${1:-}}"
transport_fixture="${FEATURE_002_TRANSPORT_FIXTURE:-tests/fixtures/transport_events/connected.json}"
conversation_fixture="${FEATURE_002_CONVERSATION_FIXTURE:-tests/fixtures/conversations/interested_callback_requested.json}"
slice1_config="${FEATURE_002_SLICE1_CONFIG:-config/slice1.toml}"
slice2_config="${FEATURE_002_SLICE2_CONFIG:-config/slice2.toml}"
test_env_file="${OPENCLOSER_TEST_ENV_FILE:-$repo_root/.env.opencloser-tests}"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '%s\n' "$*" >&2
}

if [[ -f "$test_env_file" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$test_env_file"
  set +a
  queue_item_id="${DATAVERSE_TEST_QUEUE_ITEM_GUID:-$queue_item_id}"
fi

[[ -n "$queue_item_id" ]] || fail "DATAVERSE_TEST_QUEUE_ITEM_GUID or first positional queue-item GUID is required"

if [[ ! "$queue_item_id" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
  fail "queue item id must be a Dataverse GUID in 8-4-4-4-12 hex form"
fi

for path in "$slice1_config" "$slice2_config" "$transport_fixture" "$conversation_fixture"; do
  [[ -f "$path" ]] || fail "required file not found: $path"
done

command -v uv >/dev/null 2>&1 || fail "uv is not available on PATH"

for var_name in DATAVERSE_ENV_URL DATAVERSE_TENANT_ID DATAVERSE_CLIENT_ID DATAVERSE_CLIENT_SECRET; do
  [[ -n "${!var_name:-}" ]] || fail "missing required Dataverse environment variable: $var_name"
done

uv run python - "$slice2_config" <<'PY'
import json
import re
import sys
import tomllib
from pathlib import Path

slice2_path = Path(sys.argv[1])
config = tomllib.loads(slice2_path.read_text(encoding="utf-8"))

errors: list[str] = []
run = config.get("run", {})
dataverse = config.get("dataverse", {})
task_owners = config.get("task_owners", {})
redaction = config.get("redaction", {})

campaign = str(run.get("campaign", "")).strip()
if not campaign:
    errors.append("[run].campaign is empty in config/slice2.toml")

callable_status = str(dataverse.get("callable_status", "")).strip()
if not callable_status:
    errors.append("[dataverse].callable_status is empty in config/slice2.toml")

guid_re = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
for key in ("callback", "review"):
    value = str(task_owners.get(key, "")).strip()
    if not value or value == "REPLACE_WITH_DATAVERSE_OWNER_OR_TEAM_ID":
        errors.append(f"[task_owners].{key} is still a placeholder")
    elif not guid_re.fullmatch(value):
        errors.append(f"[task_owners].{key} must be a Dataverse owner/team GUID")

policy = str(redaction.get("policy", "")).strip()
retention = str(redaction.get("retention", "")).strip()
if policy not in {"regex", "noop"}:
    errors.append("[redaction].policy must be 'regex' or 'noop'")
if retention not in {"full", "summary-only"}:
    errors.append("[redaction].retention must be 'full' or 'summary-only'")

mapping_path = Path(str(dataverse.get("mapping_artifact", ""))).expanduser()
if not mapping_path.is_file():
    errors.append(f"mapping artifact not found: {mapping_path}")
else:
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if mapping.get("_meta", {}).get("approved") is not True:
        errors.append(f"{mapping_path} has _meta.approved != true")

if errors:
    for error in errors:
        print(f"preflight: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"preflight: campaign configured, callable_status={callable_status}, mapping approved", file=sys.stderr)
PY

note "preflight: opencloser CLI available"
uv run opencloser --help >/dev/null

dry_run_command=(
  uv run opencloser run-crm
  --queue-item-id "$queue_item_id"
  --transport-fixture "$transport_fixture"
  --conversation-fixture "$conversation_fixture"
  --config "$slice1_config"
  --slice2-config "$slice2_config"
)

note "demo: running Feature 002 dry-run rehearsal; no --write flag is present"
"${dry_run_command[@]}"

if [[ "${FEATURE_002_ENABLE_WRITE:-0}" != "1" ]]; then
  note "demo: dry-run complete. Write-enabled mode was not requested."
  note "demo: to mutate the dedicated test record, set FEATURE_002_ENABLE_WRITE=1 plus the two GUID confirmation variables shown in --help."
  exit 0
fi

[[ "${FEATURE_002_TEST_RECORD_CONFIRMED:-}" == "$queue_item_id" ]] ||
  fail "FEATURE_002_TEST_RECORD_CONFIRMED must exactly equal the queue item GUID before write-enabled mode"

[[ "${FEATURE_002_PREDEMO_STATE_CAPTURED:-}" == "$queue_item_id" ]] ||
  fail "FEATURE_002_PREDEMO_STATE_CAPTURED must exactly equal the queue item GUID after pre-demo CRM state is captured"

write_command=(
  uv run opencloser run-crm
  --write
  --queue-item-id "$queue_item_id"
  --transport-fixture "$transport_fixture"
  --conversation-fixture "$conversation_fixture"
  --config "$slice1_config"
  --slice2-config "$slice2_config"
)

note "demo: running write-enabled Feature 002 demo against confirmed dedicated test record"
"${write_command[@]}"
