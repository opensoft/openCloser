# Source this file from bash or zsh to enable openCloser Speckit worktree helpers.
#
# NOTE: Prefer the container-wide `ctinit` command (defined in /etc/skel/.zshrc)
# which loads project-agnostic helpers from /usr/local/share/ct/ct-functions.zsh.
# This file is kept as a per-repo fallback for environments without the
# container-level helpers.

# Auto-detect repo root from this script's own location so the file is
# relocatable and does not embed a host-specific absolute path.
if [ -n "${ZSH_VERSION:-}" ]; then
  OPENCLOSER_SPECKIT_REPO_ROOT="$(CDPATH="" cd "${${(%):-%x}:A:h}/../.." 2>/dev/null && pwd)"
else
  OPENCLOSER_SPECKIT_REPO_ROOT="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." 2>/dev/null && pwd)"
fi
OPENCLOSER_SPECKIT_LAST_WORKTREE_SCRIPT="$OPENCLOSER_SPECKIT_REPO_ROOT/.specify/extensions/git/scripts/bash/get-last-worktree.sh"
OPENCLOSER_SPECKIT_SELECT_WORKTREE_SCRIPT="$OPENCLOSER_SPECKIT_REPO_ROOT/.specify/shell/select-worktree.sh"

_opencloser_speckit_prompt_cli() {
  local selection cli_name cli_command status

  while true; do
    printf '1. Anthropic' >&2
    if command -v claude >/dev/null 2>&1; then
      printf ' [available]\n' >&2
    else
      printf ' [not installed]\n' >&2
    fi

    printf '2. Codex' >&2
    if command -v codex >/dev/null 2>&1; then
      printf ' [available]\n' >&2
    else
      printf ' [not installed]\n' >&2
    fi

    printf '3. Gemini' >&2
    if command -v gemini >/dev/null 2>&1; then
      printf ' [available]\n' >&2
    else
      printf ' [not installed]\n' >&2
    fi

    printf 'Select AI CLI [1] (q to cancel): ' >&2
    if ! IFS= read -r selection; then
      echo >&2
      return 1
    fi

    selection="${selection#"${selection%%[![:space:]]*}"}"
    selection="${selection%"${selection##*[![:space:]]}"}"
    if [ -z "$selection" ]; then
      selection=1
    fi

    case "$selection" in
      q|Q)
        return 1
        ;;
      1)
        cli_name="Anthropic"
        cli_command="claude"
        ;;
      2)
        cli_name="Codex"
        cli_command="codex"
        ;;
      3)
        cli_name="Gemini"
        cli_command="gemini"
        ;;
      *)
        echo "Invalid selection. Enter 1-3 or q." >&2
        continue
        ;;
    esac

    if ! command -v "$cli_command" >/dev/null 2>&1; then
      echo "$cli_name CLI is not installed on PATH." >&2
      continue
    fi

    printf '%s\n' "$cli_command"
    return 0
  done
}

_opencloser_speckit_select_worktree() {
  local target

  if [ ! -f "$OPENCLOSER_SPECKIT_SELECT_WORKTREE_SCRIPT" ]; then
    echo "worktree selector not found: $OPENCLOSER_SPECKIT_SELECT_WORKTREE_SCRIPT" >&2
    return 1
  fi

  target=$(bash "$OPENCLOSER_SPECKIT_SELECT_WORKTREE_SCRIPT" --path) || return 1
  if [ -z "$target" ]; then
    echo "no Speckit worktree selected" >&2
    return 1
  fi

  printf '%s\n' "$target"
}

_opencloser_speckit_start_cli() {
  local cli_command="$1"
  local target="$2"
  shift 2 || true

  cd "$target" || return 1
  "$cli_command" "$@"
}

ct() {
  local target

  if [ ! -f "$OPENCLOSER_SPECKIT_LAST_WORKTREE_SCRIPT" ]; then
    echo "ct: helper script not found: $OPENCLOSER_SPECKIT_LAST_WORKTREE_SCRIPT" >&2
    return 1
  fi

  target=$(bash "$OPENCLOSER_SPECKIT_LAST_WORKTREE_SCRIPT") || return 1
  if [ -z "$target" ]; then
    echo "ct: no Speckit worktree path returned" >&2
    return 1
  fi

  cd "$target" || return 1
}

ctp() {
  if [ ! -f "$OPENCLOSER_SPECKIT_LAST_WORKTREE_SCRIPT" ]; then
    echo "ctp: helper script not found: $OPENCLOSER_SPECKIT_LAST_WORKTREE_SCRIPT" >&2
    return 1
  fi

  bash "$OPENCLOSER_SPECKIT_LAST_WORKTREE_SCRIPT" --json
}

cta() {
  local target

  if ! command -v claude >/dev/null 2>&1; then
    echo "cta: Claude CLI not found on PATH" >&2
    return 1
  fi

  target=$(_opencloser_speckit_select_worktree) || return 1
  _opencloser_speckit_start_cli claude "$target" "$@"
}

ctc() {
  local target

  if ! command -v codex >/dev/null 2>&1; then
    echo "ctc: Codex CLI not found on PATH" >&2
    return 1
  fi

  target=$(_opencloser_speckit_select_worktree) || return 1
  _opencloser_speckit_start_cli codex "$target" "$@"
}

ctg() {
  local target

  if ! command -v gemini >/dev/null 2>&1; then
    echo "ctg: Gemini CLI not found on PATH" >&2
    return 1
  fi

  target=$(_opencloser_speckit_select_worktree) || return 1
  _opencloser_speckit_start_cli gemini "$target" "$@"
}

cts() {
  local target
  local cli_command

  target=$(_opencloser_speckit_select_worktree) || return 1
  cli_command=$(_opencloser_speckit_prompt_cli) || return 1
  _opencloser_speckit_start_cli "$cli_command" "$target" "$@"
}

ctlist() {
  if [ ! -f "$OPENCLOSER_SPECKIT_SELECT_WORKTREE_SCRIPT" ]; then
    echo "ctlist: helper script not found: $OPENCLOSER_SPECKIT_SELECT_WORKTREE_SCRIPT" >&2
    return 1
  fi

  bash "$OPENCLOSER_SPECKIT_SELECT_WORKTREE_SCRIPT" --list
}
