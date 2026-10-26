@README.md

If your tool does not expand the import above, read `README.md` first.

# Agent Guidelines & Behavior

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

# Project

## Language

Reply in the language the prompt is written in. Everything committed to the
repo, whether code, comments, commit messages, README, docs or UI text, is in
English.

## Answers

Lead with the answer, and keep it short. Recommend one path once a choice is
clear; enumerate alternatives only in the case §1 describes. Verify versions,
flags and APIs against the installed tooling or the official docs before
stating them. Do not answer from memory.

Break it up. Short paragraphs, lists, tables. One idea per line. Never a wall of
text to wade through.

## Copy

Never use an em dash in user-facing text (UI labels, headings, error messages),
README.md, or docs. End the sentence and start a new one, or use a comma or
colon. Anywhere else is fine.

## Architecture rules

The Python side owns the data, the database and every calculation. The Next.js
side only displays what the API returns: no database, no business logic.

- `backend/forecheck/domain` is pure Python: no framework, no I/O, no clock.
  It may import only the standard library and itself.
- `application` holds the use cases and the ports (interfaces). It imports
  `domain` and nothing from the frameworks.
- `infrastructure` holds the adapters (Open-Meteo, IMGW, Postgres, the system
  clock). It implements the ports.
- `entrypoints/http` is FastAPI. It wires the adapters to the use cases.
- The direction is `entrypoints → infrastructure → application → domain`.
  `import-linter` enforces it in CI (`[tool.importlinter]` in `pyproject.toml`).
- The browser never talks to Open-Meteo or IMGW. Only the collection route does.
- The API contract is the OpenAPI document. `src/lib/api/schema.ts` is
  generated from it with `npm run api:types`. Never edit it by hand.

## Data rules

- Ground truth is IMGW station measurements only. Reanalysis (for example ERA5)
  is a model, not a measurement, so it is never used as truth.
- A forecast is stored with `issued_at`, `valid_at` and `lead_days`. Never
  score a forecast that was refreshed shortly before its valid date.
- Every day is a UTC day, for forecasts and for measurements alike.
- Every screen that shows data carries both attributions (Open-Meteo, IMGW and
  the processing notice), verbatim from `src/lib/attribution.ts`. Do not
  paraphrase them: the IMGW wording is a licence condition.
- No ads, no subscriptions, no paid APIs. The Open-Meteo free tier is for
  non-commercial use only.

## Documentation

[`README.md`](README.md) is imported at the top of this file, so it is always in
context. Keep it current. Everything else lives in [`docs/`](docs/), which is
**not** loaded automatically: read what is relevant before acting there.

Whichever one a change makes stale, update it in the same change rather than
later. When code or architecture changes, check if existing docs need updates or
if a new doc is genuinely needed (keep docs lean; only add docs that are truly
necessary). This file is part of that rule too: when a workflow, command, path
or rule it names changes, update `AGENTS.md` in the same change.

## Agent neutrality

Keep the repo usable by any coding agent. When there is an agent-specific
pattern and an agent-neutral standard for the same thing, use the standard.
For example, instructions live in `AGENTS.md`, not `CLAUDE.md` or `GEMINI.md`.
Add agent-specific files or config only when no neutral option exists.

## Secrets

Treat the repository and its entire history as public. Before every commit:

- Never commit `.env`, keys, tokens, connection strings
  with credentials, or personal settings files. Only `.env.example` files with
  placeholders belong in git.
- Check `git status` and `git diff` first. Never run a blind `git add -A`.
- Do not put secret values in code, docs, tests, logs, commit messages, or chat.
- Keep personal files ignored: `plans/`, `dev-only/`.
- If a secret ever leaks, rotate it first. Removing it from git does not undo
  the exposure.

## Commits

Conventional Commits: `type(scope): subject`, in English, imperative mood.

## Dev only

`dev-only/` is a gitignored scratch space for prototypes, mocks and experiments.
