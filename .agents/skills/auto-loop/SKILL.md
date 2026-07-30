---
name: auto-loop
description: "Autonomous delivery loop: run the board-tick digest, take the highest-signal task routed to Loop=auto on the gaarutyunov GitHub Project board (project #6), and drive it end-to-end WITHOUT human gates — never waits for owner spec approval or human code review; self-merges each PR once CI is green, then moves the task to Done. Never splits an issue into sub-issues: each issue is one deliverable, worked to merged in a single tick. Still obeys owner comments surfaced by the digest, uses labels for intermediate states, parks a genuine dependency on another issue in the Blocked status (a merely *technical* blocker is cleared in the same PR instead), and never asks anything in the Claude Code window. Use when asked to run the board unattended / fully autonomously. Examples: \"auto-run the board\", \"run the auto loop\", \"work the board without stopping for review\", \"drive the tasks and merge when CI passes\". For the gated, review-first variant, use the hitl-loop skill instead."
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

The **board-tick digest**, the **label protocol**, the **comment ack ledger**,
**GitHub-only interaction**, the **Blocked vs In review** rule, board IDs,
clone/worktree + gortex tracking, opening a PR early, the OpenSpec `/opsx:*`
flow, commit/push discipline, moving a task's status, and the
`coderabbit-prompts.py` helper are all documented **once** in the `loop-common`
skill — read `.claude/skills/loop-common/SKILL.md`. This file specifies only what
differs in the **autonomous path**: `Loop = auto` and self-merging on green CI.

## Five rules that override everything else

1. **Start with the digest.** Never query the board or read comments by hand —
   the digest is how an unattended tick sees owner direction at all:

   ```bash
   .claude/skills/loop-common/scripts/board-tick.py --loop auto
   ```

   Its `HUM` column is every owner comment you have not yet acted on. A comment
   left between ticks is a directive that outranks the issue text. Act on it,
   then **ack** it (`loop-common` → *Comments: read → act → ack*); an unacked
   comment re-surfaces every tick until you do.

2. **Never ask the owner anything in the Claude Code window.** No
   `AskUserQuestion`, ever — nobody is watching an unattended run. If you truly
   need the owner, post the question on the issue, add `needs:input`, move the
   item to **In review** — a human need is always **In review**, never
   **Blocked** — and continue with the next task.

3. **Never park a task In progress.** *In progress* means actively being worked
   this tick. Anything waiting on a *human* goes to **In review** with a label
   saying why; anything waiting on *another issue* goes to **Blocked** with that
   issue recorded as a dependency. Neither ever stays In progress.

4. **Never split an issue into sub-issues.** Every issue is one deliverable unit
   of work, finished in place — see *One issue, one deliverable* below. This
   rule outranks any instinct to break work down.

5. **Never do the work yourself.** Research, implementation, debugging and
   verification are dispatched to **child agents** with detailed, self-contained
   instructions (`loop-common` → *The loop delegates*). The loop runs the digest,
   picks the task, moves the board, talks to the owner and holds the merge gate —
   nothing else.

## Prerequisites

Same as `loop-common`: `gh` authenticated with the `project` scope
(`gh auth refresh -s project`); OpenSpec initialized in this workspace repo; code
repos cloned/worktree'd under `projects/`; `board-tick.py init-labels --repo <repo>`
run once per repo so the loop labels exist.

## The workflow (per tick)

### 1. Run the digest and choose one task

```bash
.claude/skills/loop-common/scripts/board-tick.py --loop auto
```

Work the top actionable row (`HUMAN-INPUT` → `UNBLOCKED` → `UNPUSHED` →
`SPEC-MERGED` → `CI-RED` → `THREADS` → `READY` → `NOT-STARTED` → `WIP`), skipping
`TRACKER`, `WAITING-OWNER` and `BLOCKED`. Capture the row's item id (in the
details block), issue (repo + number), and title. A Ready issue with
no Loop value (or `Loop = hitl`) is **not** this loop's — leave it untouched. If
nothing is actionable, stop (or idle on the next tick when looping).

**`UNBLOCKED` is actionable and ranks second.** Every blocker it recorded has
closed (`BLK` reads `n/n✓`), so it is work waiting to be resumed: run
`board-tick.py unblock --repo <repo> --issue <N>`, move it back to **Ready**
(`61e4505c`) and then take it through this tick like any other pickup. Only
`BLOCKED` — at least one blocker still open — is a skip.

Fix any `⚠` hygiene warning on the row in the same tick. If the chosen row is
`READY`, move it to **In progress** (`47fc9ee4`) with the status-edit command in
`loop-common`.

Note that `PR-APPROVED` / `SPEC-APPROVED` rows are not gates for this loop — it
merges on green CI without waiting for either label — but if the owner *has*
labelled one, that's still a green light, not something to undo.

### 1a. One issue, one deliverable — finish it, never split it

**Do not decompose an issue into sub-issues. Ever.** An issue is a deliverable
unit of work: this tick takes it from Ready to merged. Filing children instead of
shipping is how the loop stops delivering — every tick ends with more backlog and
nothing merged, and the real work disappears behind `tracker` labels and the
**Blocked** status that later ticks skip.

So, when an issue looks large:

- **Work it end to end in one PR.** Size is not a reason to split.
- **Write the parts as a checklist in the issue body** and tick them off as they
  land — a GitHub task list on the issue itself is the tracking record. **The
  issue is done only once the whole checklist is implemented.**
- **Drive the tick with a session todo list** (`TaskCreate` / `TaskUpdate`)
  alongside it — never as GitHub issues, and never as new board items. The
  checklist is also the dispatch plan: each item is a piece a child agent can be
  given on its own.
- **Decompose on the spec level if you need structure.** An OpenSpec change's
  `tasks.md` is the only sanctioned place to break work into steps
  (`loop-common` → *OpenSpec `/opsx:*` spec flow*). That is task decomposition,
  not issue decomposition.

And when an issue looks blocked:

- **Re-check the blocker before believing it.** The digest does this for you: the
  `BLK` column reads `closed/total` from the issue's recorded dependencies, and a
  `✓` means nothing is blocking it any more. A claim in an older comment that
  contradicts the digest is simply stale.
- **If the blocker is technical, clear it inside this issue.** Implement the
  missing piece in the same PR rather than filing it as foundation work for a
  later tick. The **Blocked** status changes nothing about this, and this is the
  common case: a gap you could close yourself is not a dependency.
- **Only a genuine dependency on another issue earns Blocked** — that issue has
  to land before this one can be finished at all. Record it and move the item to
  **Blocked** (`8351b71b`), then pick up the next task:

  ```bash
  .claude/skills/loop-common/scripts/board-tick.py block \
    --repo <repo> --issue <N> --on <ref> --note "<what is blocked, and why>"
  ```

- **Only a blocker that genuinely needs the owner** — a credential, an access
  grant, a product decision nobody else can make — goes back to them: post it on
  the issue with `board-tick.py post`, add `needs:input`, move the item to
  **In review** (`df73e18b`), and pick up the next task.

Never park either one In progress, and never reach for **Blocked** to end a tick
early. It means "another issue must land first" and nothing else.

Review comments follow the same rule: **every actionable review comment is
implemented inside the issue being worked**, never deferred to a follow-up issue,
unless the owner explicitly asks for it to be split out.

### 2. Get the code repo ready, open a PR, triage

Follow `loop-common` verbatim: clone once into `projects/<repo>`, add a per-task
worktree from fresh `origin/<default>`, `gortex track` the base + worktree, run
`board-tick.py init-labels --repo <repo>` if the loop labels aren't there yet,
open the PR early with `--body "Closes #<N>"`, then triage **spec-first vs
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

### 3. Dispatch the work, then check what came back

**The work is done by child agents, not by this loop** (`loop-common` → *The loop
delegates*). Break the checklist into pieces that can be worked independently,
dispatch them in parallel in one message, and give each one the worktree path,
the spec sections to read, the non-negotiable constraints, the acceptance
commands and what to report back.

The constraints every dispatch repeats, because a fresh agent does not know them:
**never `git add -A`** — stage named paths and inspect `git diff --cached`, commit
referencing the issue, push; testify for assertions; generated uber-gomock for
interface doubles; never create sub-issues; implement review feedback in place.

When a report comes back, **check it rather than believing it**: re-run the
digest, confirm the commits exist and contain what was claimed, and tick the
issue checklist only for what actually landed. Ensure the PR body links the issue
(`Closes #<N>`).

### 4. Merge when CI is green (the only gate)

**Re-run the digest for this task first** — `board-tick.py --repo <repo>` — so you
don't merge over feedback the owner left on the open PR since you started. Its
`HUM` count must be zero (act on and ack anything it shows) before you merge.
Then enable auto-merge so the PR merges itself the moment required checks pass:

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
  checks re-run. If it is red because the task needs something that isn't on
  `main` yet, **build that something in this PR** — a missing foundation is part
  of the deliverable, not a reason to file follow-up work. Only escalate to the
  owner when the fix genuinely requires them (step 1a). **Never merge red.**
- **Bots never gate the merge.** You *may* fold in already-posted CodeRabbit
  findings opportunistically (via `loop-common`'s **CodeRabbit + review threads**
  section), but do **not** wait for CodeRabbit or for any human review, and do
  not block on a rate-limited/limit-reached bot.

### 5. Move the task to **Done**

**Check the issue's checklist first.** The issue is done only once every box is
implemented; an unchecked box means the tick is not finished, whatever the PR
looks like. Tick the boxes the merge just delivered, and if any remain, keep
working them rather than closing the task out.

Once the checklist is complete, drop any loop labels it still carries and close
it out:

```bash
.claude/skills/loop-common/scripts/board-tick.py label \
  --repo <repo> --issue <N> --remove needs:review --remove blocked
gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id <ITEM_ID> \
  --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id 98236657
```

If the task ever carried a recorded blocker, drop the dependency too —
`board-tick.py unblock --repo <repo> --issue <N>` — so a merged issue doesn't
leave a stale edge behind.

Report: task title, merged PR URL, spec PR URL (if any), and what shipped.

## Looping

Drive continuously with `/loop` (e.g. `/loop /auto-loop`, or `/loop 15m …`). Each
iteration starts with the digest and takes **one task from Ready all the way to
merged + Done**. That is the only successful shape of a tick. Unlike `hitl-loop`,
there is **no spec-approval hard gate**, so a task is never parked waiting on a
human review.

A tick that ends without something merged has not delivered — and filing
sub-issues is not delivery. Large means "work a long tick", technically blocked
means "clear the blocker in this PR"; neither means "split it up" (step 1a). Only
two things leave a tick unmerged: a task that genuinely needs the *owner*, which
goes to **In review** with `needs:input`, and a task that genuinely depends on
*another issue*, which goes to **Blocked** with that dependency recorded. Never
leave either In progress, never use **Blocked** for work you simply haven't done,
and never ask in the chat. If nothing is actionable for **Loop = auto**, idle
until the next tick.

## Related skills

- `loop-common` — the shared board/clone/PR/spec/comments mechanics this loop builds on.
- `hitl-loop` — the gated, review-first variant (owner approves specs; humans
  review and merge).
- `pet-project-metadata`, `subdomain-setup`, `ui-kit`, `icon-generation` — same
  supporting skills `hitl-loop` lists.
