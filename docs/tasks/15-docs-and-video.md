# 15 – Video outline
Status: todo
Owner: pair (agent drafts the outline, Alex records the video)
Depends on: 14

## Goal
Write a short bullet-point outline at `~/flightboard-video-outline.md`, outside the repository,
for Alex to use as a reference while recording the video.

## Context
- `docs/documentation.md`: Purpose and Phases 1–3
- `docs/PROGRESS.md`: problems and solutions for each task
- `docs/research.md`: what was known about the original app and the API
- `README.md`: features and project structure
- `src/flightboard/`: the layers themselves

## Acceptance criteria
- [ ] Purpose: what the app is (a terminal flight board on the Swedavia FlightInfo API v2 that
      recreates an existing app) and why it was built
- [ ] System overview: one or two bullets for each part (`domain`, `api`, `services`, `cli`,
      `data`, `__main__.py` as the composition root, `tests/`) and how they depend on each other
- [ ] Each phase explained briefly: research, implementation (including completion), conclusion
- [ ] The bigger problems along the way and how each was solved, taken from `docs/PROGRESS.md`
      and the problem sections in `docs/documentation.md`. Nothing invented
- [ ] Bullet points only, short enough to glance at while recording
- [ ] Written only to `~/flightboard-video-outline.md`

## Outside the repository
This task leaves the repository untouched. It overrides these `/next-task` steps:
- Step 1: don't change this file's `Status:`.
- Steps 4–6: no tests and no reviewer pass, because there is no code or repository change.
- Step 7: no PROGRESS.md entry.
- Step 8: no `git add`. Don't create, change or stage any file inside the repository.

Hand off with the usual message, with "staged" replaced by the outline's path.

## Notes
- `README.md` and `documentation.md` Phases 2 and 3 were written ahead of this task
  (2026-11-25). Alex writes Phase 4 and the Conclusion himself.
