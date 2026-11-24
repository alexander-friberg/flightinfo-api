---
name: next-task
description: Pick the next task from docs/tasks, build it test-first, get it reviewed, log it in PROGRESS.md and stage it for Alex to commit. Optionally pass a task number.
argument-hint: "[task number]"
disable-model-invocation: true
---

# Next task

Do exactly ONE task, then stop. Alex reviews the staged changes and commits them himself.

## 0. Preconditions
- Run `git status`. If there are staged or unstaged changes left over from a previous task, stop
  and tell Alex to commit them first. Do not touch them.
- If `.claude/BLOCKED` exists, show its contents and stop. Alex deletes it once the blocker
  is resolved.

## 1. Pick the task
- If an argument was given (`$ARGUMENTS`), use the task file with that number.
- Otherwise, pick the lowest-numbered file in `docs/tasks/` with `Status: todo` whose
  `Depends on:` tasks all have `Status: done`.
- If nothing is ready, say which tasks are waiting on what, and stop.
- Set the task's `Status:` to `in-progress`.

## 2. Understand it
- Read the task file, the sections it links to in `docs/research.md` / `docs/documentation.md`,
  and the code it builds on.
- If something is ambiguous, contradicts the docs, or needs a decision only Alex can make, ask
  him before writing code. Note his answer in the task file under `## Notes`.
- If the task needs Alex to do something first (e.g. put the API key in `.env`), tell him what
  and stop.

## 3. Plan
State a short plan: files to create or change, and the tests that will prove each acceptance
criterion.

## 4. Tests first
Write the tests for the acceptance criteria. Run them and confirm they fail for the expected
reason (not because of an import error or a typo).

## 5. Implement
Write the smallest code that makes the tests pass while following every rule in `CLAUDE.md`.
Then run all checks:
`uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`

## 6. Review
Ask the `reviewer` subagent to review the current changes against `CLAUDE.md` and this task's
acceptance criteria. Fix every "Must fix" finding, then re-run all checks. You may decline a
"Should fix" finding, but say why in the handoff.

## 7. Record
- In the task file, tick the acceptance criteria and set `Status: done`.
- Append an entry to `docs/PROGRESS.md` using the template in that file. Be specific in
  "Problems & solutions": Alex uses this log to write his project documentation.

## 8. Stage
`git add` this task's files with explicit paths, including the task file and `docs/PROGRESS.md`.
Never use `git add -A`. Never commit.

## 9. Hand off
Finish with this message and nothing more:

```
## Task NN – <title>: staged

### Summary
<2–4 bullets: what changed>

### How it works
<A plain explanation of the design and the key code paths, written so Alex can explain it in
his video: which dependency is injected where, and why.>

### Look closely at
<files/lines that deserve a careful read in `git diff --staged`>

### Review
<reviewer findings and what was done about each>

### Next
<the next ready task, and anything Alex must do before it>
```

## If you get stuck
If all checks still fail after three genuine attempts, or the task can't be done as written:
1. Set the task's `Status:` to `blocked` and explain why under `## Notes`.
2. Write a one-paragraph explanation to `.claude/BLOCKED` (this lets the Stop hook allow you
   to finish).
3. Add a PROGRESS.md entry, then stop without staging anything.
