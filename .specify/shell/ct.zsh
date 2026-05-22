# Source this file from zsh to enable openCloser Speckit worktree helpers.
#
# Example:
#   source /home/brett/projects/openCloser/.specify/shell/ct.zsh

SCRIPT_DIR="${${(%):-%x}:A:h}"
source "$SCRIPT_DIR/worktrees.sh"
