#!/usr/bin/env bash

set -euo pipefail

JSON_MODE=false
if [ "${1:-}" = "--json" ]; then
    JSON_MODE=true
fi

trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

resolve_config_value() {
    local repo_root="$1"
    local key="$2"
    local default_value="$3"
    local config_file="$repo_root/.specify/extensions/git/git-config.yml"

    if [ ! -f "$config_file" ]; then
        printf '%s\n' "$default_value"
        return 0
    fi

    local raw_value
    raw_value=$(awk -F':' -v key="$key" '$1 == key {sub(/^[^:]*:[[:space:]]*/, "", $0); print $0; exit}' "$config_file")
    raw_value=$(trim "${raw_value:-}")
    if [ -z "$raw_value" ]; then
        printf '%s\n' "$default_value"
    else
        printf '%s\n' "$raw_value"
    fi
}

resolve_worktree_root() {
    local repo_root="$1"
    local default_root="../$(basename "$repo_root")-worktrees"
    local raw_root
    raw_root=$(resolve_config_value "$repo_root" "worktree_root" "$default_root")

    if [[ "$raw_root" = /* ]]; then
        printf '%s\n' "$raw_root"
    else
        local combined="$repo_root/$raw_root"
        local parent_dir
        parent_dir=$(dirname "$combined")
        local leaf_name
        leaf_name=$(basename "$combined")
        if [ -d "$parent_dir" ]; then
            printf '%s/%s\n' "$(cd "$parent_dir" && pwd -P)" "$leaf_name"
        else
            printf '%s\n' "$combined"
        fi
    fi
}

canonicalize_if_dir() {
    local candidate="$1"
    if [ -d "$candidate" ]; then
        (cd "$candidate" && pwd -P)
    else
        printf '%s\n' "$candidate"
    fi
}

emit_result() {
    local branch_name="$1"
    local worktree_path="$2"
    local base_branch="$3"
    local repo_root="$4"
    local source="$5"

    if $JSON_MODE; then
        if command -v jq >/dev/null 2>&1; then
            jq -cn \
                --arg branch_name "$branch_name" \
                --arg worktree_path "$worktree_path" \
                --arg base_branch "$base_branch" \
                --arg repo_root "$repo_root" \
                --arg source "$source" \
                '{BRANCH_NAME:$branch_name,WORKTREE_PATH:$worktree_path,BASE_BRANCH:$base_branch,REPO_ROOT:$repo_root,SOURCE:$source}'
        elif command -v python3 >/dev/null 2>&1; then
            python3 - "$branch_name" "$worktree_path" "$base_branch" "$repo_root" "$source" <<'PY'
import json
import sys

print(json.dumps({
    "BRANCH_NAME": sys.argv[1],
    "WORKTREE_PATH": sys.argv[2],
    "BASE_BRANCH": sys.argv[3],
    "REPO_ROOT": sys.argv[4],
    "SOURCE": sys.argv[5],
}))
PY
        else
            printf '{"BRANCH_NAME":"%s","WORKTREE_PATH":"%s","BASE_BRANCH":"%s","REPO_ROOT":"%s","SOURCE":"%s"}\n' \
                "$branch_name" "$worktree_path" "$base_branch" "$repo_root" "$source"
        fi
    else
        printf '%s\n' "$worktree_path"
    fi
}

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$REPO_ROOT" ]; then
    echo "Error: not inside a Git repository." >&2
    exit 1
fi

COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
if [ -z "$COMMON_DIR" ]; then
    echo "Error: could not resolve Git common dir." >&2
    exit 1
fi
if [[ "$COMMON_DIR" != /* ]]; then
    COMMON_DIR="$REPO_ROOT/$COMMON_DIR"
fi

STATE_FILE="$COMMON_DIR/speckit-last-worktree.json"
BASE_BRANCH=$(resolve_config_value "$REPO_ROOT" "base_branch" "main")

if [ -f "$STATE_FILE" ]; then
    WORKTREE_PATH=""
    BRANCH_NAME=""
    if command -v jq >/dev/null 2>&1; then
        WORKTREE_PATH=$(jq -r '.WORKTREE_PATH // ""' "$STATE_FILE")
        BRANCH_NAME=$(jq -r '.BRANCH_NAME // ""' "$STATE_FILE")
    elif command -v python3 >/dev/null 2>&1; then
        WORKTREE_PATH=$(python3 - "$STATE_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    print(json.load(fh).get("WORKTREE_PATH", ""))
PY
)
        BRANCH_NAME=$(python3 - "$STATE_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    print(json.load(fh).get("BRANCH_NAME", ""))
PY
)
    else
        WORKTREE_PATH=$(grep -o '"WORKTREE_PATH"[[:space:]]*:[[:space:]]*"[^"]*"' "$STATE_FILE" | sed 's/.*"\([^"]*\)"$/\1/')
        BRANCH_NAME=$(grep -o '"BRANCH_NAME"[[:space:]]*:[[:space:]]*"[^"]*"' "$STATE_FILE" | sed 's/.*"\([^"]*\)"$/\1/')
    fi

    if [ -n "$WORKTREE_PATH" ] && [ -d "$WORKTREE_PATH" ]; then
        WORKTREE_PATH=$(canonicalize_if_dir "$WORKTREE_PATH")
        emit_result "$BRANCH_NAME" "$WORKTREE_PATH" "$BASE_BRANCH" "$REPO_ROOT" "state_file"
        exit 0
    fi
fi

WORKTREE_ROOT=$(resolve_worktree_root "$REPO_ROOT")
LATEST_WORKTREE=""
if [ -d "$WORKTREE_ROOT" ]; then
    LATEST_WORKTREE=$(find "$WORKTREE_ROOT" -maxdepth 1 -mindepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR == 1 {print $2}')
fi

if [ -n "$LATEST_WORKTREE" ] && [ -d "$LATEST_WORKTREE" ]; then
    LATEST_WORKTREE=$(canonicalize_if_dir "$LATEST_WORKTREE")
    emit_result "$(basename "$LATEST_WORKTREE")" "$LATEST_WORKTREE" "$BASE_BRANCH" "$REPO_ROOT" "worktree_root_fallback"
    exit 0
fi

echo "Error: no Speckit worktree handoff has been recorded yet." >&2
exit 1
