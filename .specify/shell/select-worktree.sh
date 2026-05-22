#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH="" cd "$SCRIPT_DIR/../.." && pwd)"

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

MODE="prompt"
if [ "${1:-}" = "--path" ]; then
    MODE="path"
elif [ "${1:-}" = "--list" ]; then
    MODE="list"
elif [ $# -gt 0 ]; then
    echo "Usage: $0 [--path|--list]" >&2
    exit 1
fi

WORKTREE_ROOT=$(resolve_worktree_root "$REPO_ROOT")
if [ ! -d "$WORKTREE_ROOT" ]; then
    echo "No Speckit worktree root found at: $WORKTREE_ROOT" >&2
    exit 1
fi

mapfile -t WORKTREE_LINES < <(find "$WORKTREE_ROOT" -maxdepth 1 -mindepth 1 -type d -printf '%T@|%f|%p\n' 2>/dev/null | sort -t'|' -k1,1nr)
if [ "${#WORKTREE_LINES[@]}" -eq 0 ]; then
    echo "No Speckit worktrees found under: $WORKTREE_ROOT" >&2
    exit 1
fi

PATHS=()
BRANCHES=()
for line in "${WORKTREE_LINES[@]}"; do
    branch_name=${line#*|}
    branch_name=${branch_name%%|*}
    worktree_path=${line##*|}
    if [ -d "$worktree_path" ]; then
        PATHS+=("$(cd "$worktree_path" && pwd -P)")
        BRANCHES+=("$branch_name")
    fi
done

if [ "${#PATHS[@]}" -eq 0 ]; then
    echo "No usable Speckit worktrees found under: $WORKTREE_ROOT" >&2
    exit 1
fi

if [ "$MODE" = "list" ]; then
    for i in "${!PATHS[@]}"; do
        index=$((i + 1))
        marker=""
        if [ "$i" -eq 0 ]; then
            marker=" [default]"
        fi
        printf '%d. %s%s\n' "$index" "${BRANCHES[$i]}" "$marker"
        printf '   %s\n' "${PATHS[$i]}"
    done
    exit 0
fi

if [ "$MODE" = "path" ] && ! [ -t 0 ]; then
    printf '%s\n' "${PATHS[0]}"
    exit 0
fi

for i in "${!PATHS[@]}"; do
    index=$((i + 1))
    marker=""
    if [ "$i" -eq 0 ]; then
        marker=" [default]"
    fi
    printf '%d. %s%s\n' "$index" "${BRANCHES[$i]}" "$marker" >&2
    printf '   %s\n' "${PATHS[$i]}" >&2
done

while true; do
    printf 'Select worktree [1] (q to cancel): ' >&2
    if ! IFS= read -r selection; then
        echo >&2
        exit 1
    fi

    selection=$(trim "$selection")
    if [ -z "$selection" ]; then
        selection=1
    fi

    case "$selection" in
        q|Q)
            exit 1
            ;;
    esac

    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "${#PATHS[@]}" ]; then
        printf '%s\n' "${PATHS[$((selection - 1))]}"
        exit 0
    fi

    echo "Invalid selection. Enter 1-${#PATHS[@]} or q." >&2
done
