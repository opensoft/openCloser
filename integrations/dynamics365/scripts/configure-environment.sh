#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_FILE="${1:-"$ROOT_DIR/solution/deployment-settings.local.json"}"

API_BASE_URL="${OPENCLOSER_API_BASE_URL:-}"
TRIGGER_MODE="${OPENCLOSER_TRIGGER_MODE:-direct-api}"
POWER_AUTOMATE_TRIGGER_URL="${OPENCLOSER_POWER_AUTOMATE_TRIGGER_URL:-}"
DEFAULT_RUN_MODE="${OPENCLOSER_DEFAULT_RUN_MODE:-dry_run}"
TEST_MODE_ENABLED="${OPENCLOSER_TEST_MODE_ENABLED:-false}"
MAX_CAMPAIGN_BATCH_SIZE="${OPENCLOSER_MAX_CAMPAIGN_BATCH_SIZE:-10}"
ALLOWED_CAMPAIGN_CODES="${OPENCLOSER_ALLOWED_CAMPAIGN_CODES:-}"

case "$TRIGGER_MODE" in
  direct-api|power-automate) ;;
  *)
    echo "OPENCLOSER_TRIGGER_MODE must be direct-api or power-automate" >&2
    exit 2
    ;;
esac

case "$DEFAULT_RUN_MODE" in
  dry_run|write) ;;
  *)
    echo "OPENCLOSER_DEFAULT_RUN_MODE must be dry_run or write" >&2
    exit 2
    ;;
esac

mkdir -p "$(dirname "$OUT_FILE")"

cat >"$OUT_FILE" <<JSON
{
  "EnvironmentVariables": [
    {
      "SchemaName": "oc_OpenCloserApiBaseUrl",
      "Value": "$API_BASE_URL"
    },
    {
      "SchemaName": "oc_OpenCloserTriggerMode",
      "Value": "$TRIGGER_MODE"
    },
    {
      "SchemaName": "oc_OpenCloserPowerAutomateTriggerUrl",
      "Value": "$POWER_AUTOMATE_TRIGGER_URL"
    },
    {
      "SchemaName": "oc_OpenCloserDefaultRunMode",
      "Value": "$DEFAULT_RUN_MODE"
    },
    {
      "SchemaName": "oc_OpenCloserTestModeEnabled",
      "Value": "$TEST_MODE_ENABLED"
    },
    {
      "SchemaName": "oc_OpenCloserMaxCampaignBatchSize",
      "Value": "$MAX_CAMPAIGN_BATCH_SIZE"
    },
    {
      "SchemaName": "oc_OpenCloserAllowedCampaignCodes",
      "Value": "$ALLOWED_CAMPAIGN_CODES"
    }
  ],
  "ConnectionReferences": []
}
JSON

echo "Wrote $OUT_FILE"

