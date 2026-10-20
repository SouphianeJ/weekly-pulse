# Steward charter — <repo>

<!-- Copy this file into the repo the steward governs (not into weekly-pulse).
     Every section is required. "Unknown" is an acceptable answer; a guess is not. -->

Owner: <who validates plans and is the final call>
Charter version: <date> · Framing: https://github.com/SouphianeJ/weekly-pulse/blob/main/STEWARD.md

## Goal for the next weeks

<One or two sentences: what "moving forward" means for this repo right now.>

## Sources of truth

| What | Where | Known to be stale? |
|---|---|---|
| Roadmap | | |
| Decision log | | |
| Follow-up journal | | |
| Known traps | | |

When two sources disagree, report it; don't pick.

## Personas

| Who | What they do here | How often | What hurts them most when it breaks |
|---|---|---|---|

## Gate commands

| Gate item | Exact command or procedure | Where it runs | Notes |
|---|---|---|---|
| Unit tests | | | |
| Type checks | | | |
| Playwright | | | |
| Deploy | | | |
| Health check after deploy | | | |
| Rollback | | | |

If an item can't run from a cloud session, say so here: the steward will then escalate instead of merging.

## Neighbours map

<Modules, routes and screens that share code or data, so a change in one must be checked in the others.>

## Off limits

<Paths, components or kinds of change the steward must always leave to the owner, on top of the framing's list.>

## Executors

<How lots are implemented: sub-agent in the steward's session, a separate routine, or a mission of an existing loop. Size limit of a lot.>
