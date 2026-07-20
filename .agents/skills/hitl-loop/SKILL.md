---
name: hitl-loop
description: "Human-in-the-loop delivery loop: pull the next Ready task marked Loop=hitl on the gaarutyunov GitHub Project board (project #6) and take it through the full workflow (in progress → clone/worktree → branch + PR → triage → spec-or-implement → work → in review) with human gates — waits for owner spec approval before coding, and leaves every PR for human review and merge (never auto-merges). Use when asked to work the task board with review gates. Examples: \"work on the next task\", \"pull a task from the board\", \"run the project loop\". For unattended runs that skip the gates and self-merge on green CI, use the auto-loop skill instead."
---

# HITL task loop

Drives tasks on the personal GitHub Project board
[users/gaarutyunov/projects/6](https://github.com/users/gaarutyunov/projects/6)
through delivery, one task at a time, **with human review gates** — the owner
approves specs before implementation, and every PR waits for human review and
merge. Run it once for a single task, or drive it continuously with the `/loop`
skill (see **Looping** below). For a fully autonomous variant that skips both
gates and self-merges once CI is green, use the **auto-loop** skill.

## Shared mechanics live in `loop-common`

The board IDs, Ready-task selection, the **always-read-comments** rule,
clone/worktree + gortex tracking, opening a PR early, the OpenSpec `/opsx:*`
flow, commit/push discipline, moving a task's status, and the
`coderabbit-prompts.py` helper are all documented **once** in the `loop-common`
skill — read `.claude/skills/loop-common/SKILL.md`. This file specifies only what
is **specific to the human-gated path**: `Loop = hitl`, the spec-approval gate,
and leaving every PR for human review + merge.

> **Read the comments every time.** Per `loop-common`, before you act on a task
> in **any** active status (Ready / In progress / In review) — including each
> time you resume it or come back to its PR — read the issue's and the PR's
> comments first and treat owner comments as instructions. Only Backlog and Done
> are exempt.

## Prerequisites

Same as `loop-common`: `gh` authenticated with the `project` scope
(`gh auth refresh -s project`); OpenSpec initialized in this workspace repo; code
repos cloned/worktree'd under `projects/`.

## The workflow (per task)

### 1. Get a task from **Ready** marked **Loop = hitl**, move it to **In progress**

Use the `loop-common` **Select a Ready task** query with `LOOP=hitl`. Capture the
item id, linked issue (repo + number), and title. A Ready issue with no Loop
value (or `Loop = auto`) is **not** this loop's — leave it untouched. If there is
no eligible item, stop.

**Read the comments now** (`loop-common` → *Always read the comments*): pull the
issue's comments before doing anything, so any owner direction on the task shapes
what you build. Then move the item to **In progress** (`47fc9ee4`) with the
status-edit command in `loop-common`.

### 2. Get the code repo ready, open a PR, triage

Follow `loop-common` verbatim: clone once into `projects/<repo>`, add a per-task
worktree from fresh `origin/<default>`, `gortex track` the base + worktree, open
the PR early with `--body "Closes #<N>"`, then triage **spec-first vs
implement-directly**.

### 3. Spec-first path — **owner-approval gate**

Author the change with `loop-common`'s OpenSpec flow (`/opsx:propose …`) and open
the spec PR in this workspace repo. **Then wait for the owner to approve and merge
the spec PR** (apply the review & merge discipline in step 5). Do **not** start
implementation until it is merged.

When looping, this is a **hard gate** — leave the task in **In progress**, note
that it's awaiting review, and pick up the next Ready task (or idle) rather than
blocking the whole loop.

Once the spec PR is merged, implement from the change's `tasks.md` with
`/opsx:apply`, and `/opsx:archive` once the work has shipped. For a direct task,
skip straight to the work.

### 4. Perform the work, commit, push, move to **In review**

Implement in the branch/worktree with tests where the project has them, keeping
`loop-common`'s commit/push discipline (**never `git add -A`**; stage specific
paths, inspect `git diff --cached`, ref the issue). Once the work is pushed and
the PR links the issue (and the merged spec PR, if any), move the item to **In
review** (`df73e18b`). Never move to **In review** until the work is pushed.

Report: task title, code PR URL, spec PR URL (if any), and what was done.

### 5. Review & merge discipline — **owner merges**

**Never merge a PR/MR with unresolved review threads.** Before merging any PR (a
code PR, or a spec PR once the owner has approved it), work the threads in this
order:

1. **Owner (human) comments first.** Re-read the issue and PR comments
   (`loop-common` → *Always read the comments*) and address every review comment
   the repo owner wrote. These take priority over any bot.
2. **Then CodeRabbit comments you find valid.** Pull, verify, and resolve them
   using `loop-common`'s **CodeRabbit + review threads** section (the
   `coderabbit-prompts.py` helper + `resolveReviewThread` mutation). If
   CodeRabbit's review limit is reached, ignore it — there are no bot threads to
   work.
3. **Resolve every thread**, then **merge only once all threads are resolved and
   checks are green**:

   ```bash
   gh pr merge <PR#> --repo gaarutyunov/<repo> --squash
   ```

Unlike `auto-loop`, **this loop does not self-merge** — the owner merges the code
PR after review. The spec PR is likewise owner-merged (step 3). The same
"no unresolved threads" rule applies to both.

## Looping

Drive continuously with the `/loop` skill (e.g. `/loop /hitl-loop` for
self-paced, or `/loop 15m …`). Each iteration handles one task end-to-end:

- If there is no **Ready** task marked **Loop = hitl**, do nothing and wait for
  the next tick. (`auto`-marked and unrouted tasks are not this loop's.)
- If a task is blocked on **spec approval** (step 3), leave it in **In progress**,
  note that it's awaiting review, and pick up the next Ready task (or idle if
  none) rather than blocking the whole loop.
- Never move a task to **In review** until its work is pushed.

## Related skills

- `loop-common` — the shared board/clone/PR/spec/comments mechanics this loop builds on.
- `auto-loop` — the unattended sibling that self-merges on green CI.
- `pet-project-metadata` — ensure a new/updated repo has the required metadata.
- `subdomain-setup` — publish the result at `<name>.garutyunov.com`.
- `ui-kit` — build the UI with the shared design system.
- `icon-generation` — generate the project/app icon.
