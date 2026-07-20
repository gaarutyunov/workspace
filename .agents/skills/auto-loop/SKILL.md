---
name: auto-loop
description: "Autonomous delivery loop: pull the next Ready task marked Loop=auto on the gaarutyunov GitHub Project board (project #6) and drive it end-to-end WITHOUT human gates — never waits for owner spec approval or human code review; self-merges each PR once CI is green, then moves the task to Done. Use when asked to run the board unattended / fully autonomously. Examples: \"auto-run the board\", \"run the auto loop\", \"work the board without stopping for review\", \"drive the tasks and merge when CI passes\". For the gated, review-first variant, use the hitl-loop skill instead."
---

# Auto task loop

The **autonomous** sibling of `hitl-loop`. It drives tasks on the personal
GitHub Project board
[users/gaarutyunov/projects/6](https://github.com/users/gaarutyunov/projects/6)
through delivery one at a time, but **removes every human gate**:

- it does **not** wait for the owner to approve a spec before implementing;
- it does **not** leave PRs for human review;
- it **self-merges each PR as soon as CI is green**, then moves the task to
  **Done**.

> **Use only when the owner has opted into unattended operation.** This loop
> merges code into default branches without a human in the loop. The only merge
> gate is green CI, so the project's CI must actually be trustworthy (build +
> tests + lint on every PR). If in doubt, use `hitl-loop` instead.

## Shared mechanics live in `loop-common`

The board IDs, Ready-task selection, the **always-read-comments** rule,
clone/worktree + gortex tracking, opening a PR early, the OpenSpec `/opsx:*`
flow, commit/push discipline, moving a task's status, and the
`coderabbit-prompts.py` helper are all documented **once** in the `loop-common`
skill — read `.claude/skills/loop-common/SKILL.md`. This file specifies only what
differs in the **autonomous path**: `Loop = auto`, epic/blocked decomposition,
and self-merging on green CI.

> **Read the comments every time — even unattended.** Per `loop-common`, before
> you act on a task in **any** active status (Ready / In progress / In review) —
> including each time a later tick resumes it or returns to its PR — read the
> issue's and the PR's comments first and treat owner comments as instructions.
> Only Backlog and Done are exempt. This is how the owner steers an
> otherwise-unattended loop: a comment left between ticks is a directive, so a
> loop that never reads comments will ship work the owner already redirected.

## Prerequisites

Same as `loop-common`: `gh` authenticated with the `project` scope
(`gh auth refresh -s project`); OpenSpec initialized in this workspace repo; code
repos cloned/worktree'd under `projects/`.

## The workflow (per task)

### 1. Get a task from **Ready** marked **Loop = auto**, move it to **In progress**

Use the `loop-common` **Select a Ready task** query with `LOOP=auto`. Capture the
item id, linked issue (repo + number), and title. A Ready issue with no Loop
value (or `Loop = hitl`) is **not** this loop's — leave it untouched. If there is
no eligible item, stop (or idle on the next tick when looping).

**Read the comments now** (`loop-common` → *Always read the comments*): pull the
issue's comments before touching code, so any owner direction left on the task
shapes what you build. Then move the item to **In progress** (`47fc9ee4`) with the
status-edit command in `loop-common`.

### 1a. Epic / blocked check — decompose or unblock, never dead-end

Before touching code, judge whether the task can realistically be **implemented
and merged to Done in a single iteration**. Two conditions divert it from the
normal path — and **both are resolved the same way: research a path forward and
decompose into Ready/auto sub-issues. Never silently park a task as "blocked."**

- **Epic (too large):** it spans multiple independent subsystems/layers; it would
  run to thousands of LOC or many separate deliverables; or its body is a
  multi-part checklist where each box is itself a shippable unit. A ground-up
  reimplementation, a whole new subsystem, or "implement spec X" where X defines
  several layers is almost always an epic.
- **Blocked (can't reach merged-green this iteration):** it depends on something
  not yet on `main` — an unimplemented or unwired subsystem, unmerged/parked
  branches, an upstream fix, or an unmade design decision. A blocker is **not** a
  reason to stop; it is the signal to **research the fix or the decomposition**
  and turn it into actionable work the loop can grind down.

In either case, **do not force it through in one PR, and do not just comment
"blocked" and move on.** Research the path forward, then decompose and let the
loop grind the pieces:

1. **Research the fix / breakdown.** Understand *why* it is too big or blocked —
   read the code, the specs, the parked branches, the failing checks — then design
   the smallest set of **independently deliverable, independently mergeable**
   sub-issues, ordered so each builds only on already-merged ones (foundation /
   unblocking layers first). Each sub-issue must be sized to go Ready → merged in
   one iteration on its own. If a foundation piece is *itself* still an epic or
   still blocked, that is fine: a later iteration picks it up and decomposes it
   **again** by this same rule (recursive decomposition — the loop never
   dead-ends).
2. **Create a GitHub issue per piece** in the **code repo** (not the workspace
   repo): `gh issue create --repo gaarutyunov/<repo> --title "…" --body "…" --label auto`.
   Write a self-contained body (goal, scope, acceptance) and reference the parent
   (`Part of #<PARENT>`). Create the `auto` label first if missing
   (`gh label create auto -R gaarutyunov/<repo> --color ededed 2>/dev/null || true`).
3. **Put each sub-issue on the board as this loop's work.** Add it to project #6
   and set **Status = Ready** (`61e4505c`) and **Loop = auto** (`ee15c5cc`) so the
   **next iteration picks it up automatically**:

   ```bash
   ITEM=$(gh project item-add 6 --owner gaarutyunov --url <issue-url> --format json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
   gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id "$ITEM" \
     --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id 61e4505c   # Status=Ready
   gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id "$ITEM" \
     --field-id PVTSSF_lAHOAjGWgc4BcicezhYRXrw --single-select-option-id ee15c5cc   # Loop=auto
   ```
4. **Turn the parent into a tracking checklist.** Edit the parent body to add a
   `## Sub-issues` checklist linking every child (`- [ ] #<n> — <title>`), so the
   parent reflects progress as children merge.
5. **Park the parent as a tracker, don't finish it.** Set the parent itself to
   **In progress** (`47fc9ee4`) — it is a tracker now, not a codeable task. It
   moves to **Done** only in a later iteration once **all** its sub-issues are
   merged (verify every checklist box is checked / every child is Done before
   moving the parent).
6. **Continue.** Proceed to work the first sub-issue this iteration (steps 2–4
   below), or let the next tick pick it up. Never leave the parent itself as the
   task to "implement".

For a normally-sized, unblocked task (fits one iteration), skip all of this and go
straight to step 2.

### 2. Get the code repo ready, open a PR, triage

Follow `loop-common` verbatim: clone once into `projects/<repo>`, add a per-task
worktree from fresh `origin/<default>`, `gortex track` the base + worktree, open
the PR early with `--body "Closes #<N>"`, then triage **spec-first vs
implement-directly**.

The difference from `hitl-loop` is that **there is no human approval gate on
either path**:

- **Spec-first:** author the change with `loop-common`'s `/opsx:propose` flow,
  open the spec PR in this workspace repo, wait for **its** CI to go green, then
  **self-merge it** (`gh pr merge --squash --auto`, see step 4). Do **not** wait
  for owner approval. Then implement from `tasks.md` with `/opsx:apply`, and
  `/opsx:archive` once the work ships.
- **Direct:** go straight to the work.

Autonomy caveat: without a human approving the spec, be conservative — keep the
change scoped to exactly what the issue (and any owner comments) ask, and prefer
the direct path unless a spec genuinely reduces risk.

### 3. Perform the work, commit, push

Implement in the branch/worktree with tests where the project has them, keeping
`loop-common`'s commit/push discipline — **never `git add -A`**; stage only the
specific paths, inspect `git diff --cached`, commit referencing the issue, push.
Ensure the PR body links the issue (`Closes #<N>`).

### 4. Merge when CI is green (the only gate)

**Re-read the PR comments first** (`loop-common` → *Always read the comments*) so
you don't merge over feedback the owner left on the open PR. Then enable
auto-merge so the PR merges itself the moment required checks pass:

```bash
gh pr merge <PR#> --repo gaarutyunov/<repo> --squash --auto
```

If the repo has no branch protection (auto-merge unavailable), poll and merge:

```bash
gh pr checks <PR#> --repo gaarutyunov/<repo> --watch   # blocks until checks settle
gh pr merge  <PR#> --repo gaarutyunov/<repo> --squash  # merge once green
```

Rules:

- **Green CI is the sole merge gate.** Merge once all *required* checks pass.
- **Owner comments still come first.** If the owner commented on the issue or PR,
  address it before merging — an owner comment overrides "just merge on green".
- **If CI fails, fix it — do not merge.** Push fixes to the same branch and let
  checks re-run when the fix is small and local. If it can't be made green because
  the task depends on missing/unmerged foundations or an upstream fix, treat it as
  **blocked** and hand it back to the step 1a decomposition — research the
  unblock, file Ready/auto sub-issues for the foundation work, turn this task into
  a tracker, and move on. **Never merge red, and never leave a blocker as a bare
  "blocked" comment with no follow-up work created.**
- **Bots never gate the merge.** You *may* fold in already-posted CodeRabbit
  findings opportunistically (via `loop-common`'s **CodeRabbit + review threads**
  section), but do **not** wait for CodeRabbit or for any human review, and do
  not block on a rate-limited/limit-reached bot.

### 5. Move the task to **Done**

After the merge lands:

```bash
gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id <ITEM_ID> \
  --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id 98236657
```

Report: task title, merged PR URL, spec PR URL (if any), and what shipped.

## Looping

Drive continuously with `/loop` (e.g. `/loop /auto-loop`, or `/loop 15m …`). Each
iteration takes one task from Ready all the way to **merged + Done** — except an
**epic or a blocked task**, which an iteration instead **researches and
decomposes** into Ready/auto sub-issues and parks as a tracker (step 1a); the loop
then delivers those sub-issues on subsequent ticks (decomposing again if any is
itself still an epic or blocked) and closes the parent once all its children are
merged. Unlike `hitl-loop`, there is **no spec-approval hard gate**, so a task is
never parked waiting on a human. **The only reason to leave a task in In progress
is that it has become a tracker** — an epic or blocker this iteration decomposed
into Ready/auto sub-issues. A blocker is never a dead end: it is researched,
broken into foundation sub-issues, and those are picked up on later ticks until
the parent's children are all merged. If there is no Ready task marked
**Loop = auto**, idle until the next tick.

## Related skills

- `loop-common` — the shared board/clone/PR/spec/comments mechanics this loop builds on.
- `hitl-loop` — the gated, review-first variant (owner approves specs; humans
  review and merge).
- `pet-project-metadata`, `subdomain-setup`, `ui-kit`, `icon-generation` — same
  supporting skills `hitl-loop` lists.
