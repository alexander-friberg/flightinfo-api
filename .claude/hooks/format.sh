#!/usr/bin/env bash
# PostToolUse hook: format Python code after every Edit/Write.
# Never blocks: formatting problems are caught by checks.sh at the end of the turn.

cd "$CLAUDE_PROJECT_DIR" || exit 0
[ -f pyproject.toml ] || exit 0   # project not initialised yet (before task 01)

uv run ruff format --quiet . >/dev/null 2>&1
exit 0
