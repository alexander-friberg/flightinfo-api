#!/usr/bin/env bash
# Stop hook: Claude can't finish its turn while lint, format, types or tests fail.
# Exit code 2 blocks the stop, and stderr is fed back to Claude as the reason.

cd "$CLAUDE_PROJECT_DIR" || exit 0
[ -f pyproject.toml ] || exit 0      # project not initialised yet (before task 01)
[ -f .claude/BLOCKED ] && exit 0     # agent reported a blocker, so let it stop and explain

output=$(
  {
    uv run ruff check . &&
    uv run ruff format --check . &&
    uv run mypy &&
    uv run pytest -q
  } 2>&1
)
status=$?

if [ $status -ne 0 ]; then
  echo "Checks failed. Fix them before finishing (or follow 'If you get stuck' in next-task):" >&2
  echo "$output" | tail -n 60 >&2
  exit 2
fi

exit 0
