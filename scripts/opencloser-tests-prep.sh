#!/usr/bin/env bash

# Source this file to load openCloser-specific Dataverse test credentials into
# the current shell without adding them to the shared pyBench container config.
#
#   source scripts/opencloser-tests-prep.sh
#
# Or execute it as a command wrapper:
#
#   scripts/opencloser-tests-prep.sh -- uv run opencloser run-crm ...

_opencloser_tests_prep_script_path() {
  if [ -n "${ZSH_VERSION:-}" ]; then
    # zsh: current sourced/executed file path.
    echo "${(%):-%x}"
  elif [ -n "${BASH_VERSION:-}" ]; then
    echo "${BASH_SOURCE:-$0}"
  else
    echo "$0"
  fi
}

_opencloser_tests_prep_sourced() {
  if [ -n "${ZSH_VERSION:-}" ]; then
    case "${ZSH_EVAL_CONTEXT:-}" in
      *:file:*) return 0 ;;
      *) return 1 ;;
    esac
  fi
  if [ -n "${BASH_VERSION:-}" ]; then
    [ "${BASH_SOURCE:-$0}" != "$0" ]
    return $?
  fi
  return 1
}

_opencloser_tests_prep_root() {
  local script_dir
  script_dir="$(cd "$(dirname "$(_opencloser_tests_prep_script_path)")" && pwd)"
  cd "$script_dir/.." && pwd
}

_opencloser_tests_prep_usage() {
  cat <<'USAGE'
Usage:
  source scripts/opencloser-tests-prep.sh
  scripts/opencloser-tests-prep.sh --check
  scripts/opencloser-tests-prep.sh --init
  scripts/opencloser-tests-prep.sh -- <command> [args...]

Loads repo-local Dataverse test settings from `.env.opencloser-tests`.
The env file is intentionally ignored by git and does not affect pyBench
outside shells or commands where this prep script is used.

Optional:
  OPENCLOSER_TEST_ENV_FILE=/path/to/env source scripts/opencloser-tests-prep.sh
USAGE
}

_opencloser_tests_prep_load() {
  local repo_root env_file
  repo_root="$(_opencloser_tests_prep_root)"
  env_file="${OPENCLOSER_TEST_ENV_FILE:-$repo_root/.env.opencloser-tests}"

  if [ ! -f "$env_file" ]; then
    printf 'openCloser test env file missing: %s\n' "$env_file" >&2
    printf 'Create it with: scripts/opencloser-tests-prep.sh --init\n' >&2
    return 1
  fi

  case $- in
    *a*) local had_allexport=1 ;;
    *) local had_allexport=0 ;;
  esac

  set -a
  # shellcheck disable=SC1090
  . "$env_file"
  if [ "$had_allexport" -eq 0 ]; then
    set +a
  fi
}

_opencloser_tests_prep_check() {
  local missing=0
  local name value

  for name in DATAVERSE_ENV_URL DATAVERSE_TENANT_ID DATAVERSE_CLIENT_ID DATAVERSE_CLIENT_SECRET; do
    eval "value=\${$name:-}"
    case "$value" in
      ""|\<*)
        printf '%s=missing\n' "$name"
        missing=1
        ;;
      *)
        printf '%s=present\n' "$name"
        ;;
    esac
  done

  if [ -n "${DATAVERSE_TEST_QUEUE_ITEM_GUID:-}" ] && [ "$DATAVERSE_TEST_QUEUE_ITEM_GUID" != "<dataverse-test-queue-item-guid>" ]; then
    printf 'DATAVERSE_TEST_QUEUE_ITEM_GUID=%s\n' "$DATAVERSE_TEST_QUEUE_ITEM_GUID"
  else
    printf 'DATAVERSE_TEST_QUEUE_ITEM_GUID=missing\n'
    missing=1
  fi

  return "$missing"
}

_opencloser_tests_prep_init() {
  local repo_root target template
  repo_root="$(_opencloser_tests_prep_root)"
  target="${OPENCLOSER_TEST_ENV_FILE:-$repo_root/.env.opencloser-tests}"
  template="$repo_root/config/opencloser-tests.env.example"

  if [ -e "$target" ]; then
    printf 'openCloser test env file already exists: %s\n' "$target" >&2
    return 0
  fi

  cp "$template" "$target"
  chmod 600 "$target"
  printf 'created %s\n' "$target"
  printf 'edit it and replace placeholder tenant/client/secret values before use\n'
}

_opencloser_tests_prep_main() {
  case "${1:-}" in
    -h|--help)
      _opencloser_tests_prep_usage
      ;;
    --init)
      _opencloser_tests_prep_init
      ;;
    --check)
      _opencloser_tests_prep_load && _opencloser_tests_prep_check
      ;;
    --)
      shift
      if [ $# -eq 0 ]; then
        printf 'error: command required after --\n' >&2
        return 2
      fi
      _opencloser_tests_prep_load || return $?
      _opencloser_tests_prep_check >/dev/null || return $?
      exec "$@"
      ;;
    "")
      _opencloser_tests_prep_load && _opencloser_tests_prep_check
      ;;
    *)
      printf 'error: unknown argument: %s\n' "$1" >&2
      _opencloser_tests_prep_usage >&2
      return 2
      ;;
  esac
}

if _opencloser_tests_prep_sourced; then
  _opencloser_tests_prep_main "$@"
else
  set -eu
  _opencloser_tests_prep_main "$@"
fi
