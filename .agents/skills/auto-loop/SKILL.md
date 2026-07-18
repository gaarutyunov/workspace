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

The mechanics it shares with `hitl-loop` — board discovery, clone/worktree,
branch/PR, the OpenSpec `/opsx:*` flow, the `coderabbit-prompts.py` helper — are
**not duplicated here**; read `hitl-loop`'s SKILL.md for those. This file
specifies only what differs.

## Prerequisites

Same as `hitl-loop`: `gh` authenticated with the `project` scope
(`gh auth refresh -s project`), specs authored via OpenSpec in this workspace
repo, code repos cloned/worktree'd under `projects/` (gitignored — see the
workspace `AGENTS.md` clone rule).

## Board IDs (project #6 "growth")

Stable — skip discovery unless the schema changes:

- Project id: `PVT_kwHOAjGWgc4Bcice`
- Status field id: `PVTSSF_lAHOAjGWgc4BcicezhXKdRQ`
- Options: Backlog `f75ad846` · Ready `61e4505c` · In progress `47fc9ee4` ·
  In review `df73e18b` · Done `98236657`
- **Loop field id: `PVTSSF_lAHOAjGWgc4BcicezhYRXrw`** · options: hitl `d03523f4`
  · auto `ee15c5cc`

The **Loop** field routes each task to one loop. This skill only handles items
with **Loop = `auto`**; `hitl`-marked items belong to the `hitl-loop` skill. In
the item-list JSON the value is the top-level `loop` key.

## The workflow (per task)

### 1. Get a task from **Ready** marked **Loop = auto**, move it to **In progress**

Same as `hitl-loop` step 1 but filtered to this loop (**`loop == 'auto'`**):

```bash
gh project item-list $PROJ --owner $OWNER --format json --limit 200 \
  | python3 -c "import sys,json; \
    items=json.load(sys.stdin)['items']; \
    r=[i for i in items if i.get('status')=='Ready' \
       and i.get('loop')=='auto' \
       and i.get('content',{}).get('type')=='Issue']; \
    print(json.dumps(r[0] if r else {}, indent=2))"
```

Capture the top match's item id + linked issue + title, then set Status to
**In progress** (`47fc9ee4`). A Ready issue with **no Loop value** (or
`Loop = hitl`) is **not** this loop's — leave it untouched. If there is no
eligible item, stop (or idle on the next tick when looping).

### 1a. Epic check — decompose if too large to finish in one iteration

Before touching code, judge whether the task can realistically be **implemented
and merged to Done in a single iteration**. Treat it as an **epic** (too large)
when any of these hold: it spans multiple independent subsystems/layers; it would
run to thousands of LOC or many separate deliverables; or its body is a
multi-part checklist where each box is itself a shippable unit. A ground-up
reimplementation, a whole new subsystem, or "implement spec X" where X defines
several layers is almost always an epic.

If it is an epic, **do not try to build it all in one PR.** Instead decompose it
and let the loop grind the pieces:

1. **Design the breakdown.** Split the epic into the smallest set of
   **independently deliverable, independently mergeable** sub-issues, ordered so
   each builds only on already-merged ones (foundation layers first). Each
   sub-issue must be sized to go Ready → merged in one iteration on its own.
2. **Create a GitHub issue per piece** in the **code repo** (not the workspace
   repo): `gh issue create --repo gaarutyunov/<repo> --title "…" --body "…" --label auto`.
   Write a self-contained body (goal, scope, acceptance) and reference the epic
   (`Part of #<EPIC>`). Create the `auto` label first if missing
   (`gh label create auto -R gaarutyunov/<repo> --color ededed 2>/dev/null || true`).
3. **Put each sub-issue on the board as this loop's work.** Add it to project #6
   and set **Status = Ready** (`61e4505c`) and **Loop = auto** (`ee15c5cc`) so
   future iterations pick it up:

   ```bash
   ITEM=$(gh project item-add 6 --owner gaarutyunov --url <issue-url> --format json | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
   gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id "$ITEM" \
     --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id 61e4505c   # Status=Ready
   gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id "$ITEM" \
     --field-id PVTSSF_lAHOAjGWgc4BcicezhYRXrw --single-select-option-id ee15c5cc   # Loop=auto
   ```
4. **Turn the epic into a tracking checklist.** Edit the epic body to add a
   `## Sub-issues` checklist linking every child (`- [ ] #<n> — <title>`), so the
   epic reflects progress as children merge.
5. **Park the epic, don't finish it.** Set the epic itself to **In progress**
   (`47fc9ee4`) — it is a tracker now, not a codeable task. It moves to **Done**
   only in a later iteration once **all** its sub-issues are merged (verify every
   checklist box is checked / every child is Done before moving the epic).
6. **Continue.** Proceed to work the first sub-issue this iteration (steps 2–6
   below), or let the next tick pick it up. Never leave the epic itself as the
   task to "implement".

For a normally-sized task (fits one iteration), skip all of this and go straight
to step 2.

### 2. Get the code repo ready, branch, open a PR

Identical to `hitl-loop` steps 3–4: clone the repo **once** into
`projects/<repo>`, then add a per-task git worktree under
`projects/<repo>/.worktrees/issue-<N>` branched from **fresh `origin/<default>`**
(always `git fetch` first — never branch off a stale local main); open a PR early
with `--body "Closes #<N>"`. Index for the graph/MCP tools as you go: `gortex
track` the base clone once, and `gortex track --as-worktree <worktree-path>` each
worktree — gortex does **not** auto-index worktrees. See `hitl-loop` step 3.

### 3. Triage — spec-first vs direct (no approval gate)

Use the same spec-vs-direct judgment as `hitl-loop` step 5. The difference is
**there is no human approval gate on either path**:

- **Spec-first:** author the change with `/opsx:propose <repo>-issue-<N>-<slug>`,
  open the spec PR in this workspace repo, wait for **its** CI to go green, then
  **self-merge it** (`gh pr merge --squash --auto`, see step 5). Do **not** wait
  for owner approval. Then implement from the change's `tasks.md` with
  `/opsx:apply`, and `/opsx:archive` once the work has shipped.
- **Direct:** go straight to the work.

Autonomy caveat: without a human approving the spec, be conservative — keep the
change scoped to exactly what the issue asks, and prefer the direct path unless a
spec genuinely reduces risk.

### 4. Perform the work, commit, push

Implement in the branch/worktree with tests where the project has them. Keep the
staging discipline from `hitl-loop` step 8 — **never `git add -A`**; stage only
the specific paths, inspect `git diff --cached`, commit referencing the issue,
push. Ensure the PR body links the issue (`Closes #<N>`).

### 5. Merge when CI is green (the only gate)

Enable auto-merge so the PR merges itself the moment required checks pass:

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
- **If CI fails, fix it — do not merge.** Push fixes to the same branch and let
  checks re-run. If it can't be made green (e.g. a genuine blocker), leave the
  task in **In progress**, comment why on the issue/PR, and move on to the next
  Ready task rather than merging red or blocking the loop.
- **Bots never gate the merge.** You *may* fold in already-posted CodeRabbit
  findings opportunistically (using `hitl-loop`'s `coderabbit-prompts.py`), but
  do **not** wait for CodeRabbit or for any human review, and do not block on a
  rate-limited/limit-reached bot.

### 6. Move the task to **Done**

After the merge lands:

```bash
gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id <ITEM_ID> \
  --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id 98236657
```

Report: task title, merged PR URL, spec PR URL (if any), and what shipped.

## Looping

Drive continuously with `/loop` (e.g. `/loop /auto-loop`, or `/loop 15m …`). Each
iteration takes one task from Ready all the way to **merged + Done** — except an
**epic**, which an iteration instead decomposes into Ready sub-issues and parks
as a tracker (step 1a); the loop then delivers those sub-issues on subsequent
ticks and closes the epic once they are all merged. Unlike `hitl-loop`, there is
**no spec-approval hard gate**, so a task is never parked waiting on a human — the
only reasons to leave a task in **In progress** are an epic acting as a tracker,
or CI that can't be made green. If there is no Ready task marked **Loop = auto**,
idle until the next tick.

## Related skills

- `hitl-loop` — the gated, review-first variant (owner approves specs; humans
  review and merge). Shares the board mechanics and the `coderabbit-prompts.py`
  helper this skill refers to.
- `pet-project-metadata`, `subdomain-setup`, `ui-kit`, `icon-generation` — same
  supporting skills `hitl-loop` lists.
