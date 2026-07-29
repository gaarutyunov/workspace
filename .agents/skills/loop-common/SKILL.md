---
name: loop-common
description: "Shared mechanics for the auto-loop and hitl-loop delivery skills: the rule that all work is delegated to child agents while the loop only orchestrates, the board-tick.py digest that starts every tick, the label protocol for intermediate states, the comment ack ledger, GitHub-only interaction (never AskUserQuestion), the blocked/needs-owner → In review rule, the one-issue-one-deliverable rule (never split an issue into sub-issues), board IDs (gaarutyunov project #6), clone/worktree + gortex tracking, opening a PR early, the OpenSpec /opsx:* spec flow, commit/push discipline, and CodeRabbit + review-thread handling. NOT a standalone loop — it has no merge gate of its own; auto-loop and hitl-loop invoke it and add their own gates. Read it when running or editing either loop."
---

# Loop common mechanics

The parts of the delivery loop that **auto-loop** and **hitl-loop** share. Both
skills drive tasks on the personal GitHub Project board
[users/gaarutyunov/projects/6](https://github.com/users/gaarutyunov/projects/6),
one task at a time; they differ only in their **gates** (auto self-merges on
green CI; hitl waits for owner spec approval and human review). Everything that
is *the same either way* lives here so it is written down once.

This is **not** a loop you run on its own — it has no task-selection entry point
and no merge gate. Use `auto-loop` or `hitl-loop`; each tells you which pieces of
this file apply and layers its own gates on top.

## Prerequisites

- `gh` authenticated. **Projects v2 needs the `project` (or `read:project`)
  scope**, which is *not* in the default token here. Add it once:
  `gh auth refresh -s project`. Without it, `gh project …` returns
  `authentication token is missing required scopes [read:project]`.
- The workspace repo (this repo) is the home for **specs** — OpenSpec is
  initialized here (`/opsx:*` commands + `openspec/`). Pet-project code repos are
  cloned under `projects/` (gitignored) or worked via git worktree.
- `.claude/skills/loop-common/scripts/board-tick.py` — the digest/ack/label tool
  every tick runs through. Python 3 stdlib only; shells out to `gh`. Run
  `board-tick.py init-labels --repo <repo>` once per repo the loops touch so the
  loop label set exists there. Its parsing/classification logic is covered by
  `scripts/test_board_tick.py` — `cd` into `scripts/` and run
  `python3 -m unittest` after editing it.

## Board IDs (project #6 "growth")

Stable — skip discovery unless the board schema changes:

- Project id: `PVT_kwHOAjGWgc4Bcice`
- Status field id: `PVTSSF_lAHOAjGWgc4BcicezhXKdRQ`
- Options: Backlog `f75ad846` · Ready `61e4505c` · In progress `47fc9ee4` ·
  In review `df73e18b` · Done `98236657`
- **Loop field id: `PVTSSF_lAHOAjGWgc4BcicezhYRXrw`** · options: hitl `d03523f4`
  · auto `ee15c5cc`

To re-discover them (only if the schema changed):

```bash
OWNER=gaarutyunov
PROJ=6
gh project field-list $PROJ --owner $OWNER --format json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
    [print(f['id'], f['name'], [(o['id'],o['name']) for o in f.get('options',[])]) \
     for f in d['fields'] if f['name'] in ('Status','Loop')]"
gh project view $PROJ --owner $OWNER --format json --jq '.id'   # project node id
```

The **Loop** field routes each task to exactly one loop. `hitl`-marked items
belong to `hitl-loop`; `auto`-marked items belong to `auto-loop`. In the
item-list JSON the value appears under the top-level `loop` key. A Ready issue
with **no Loop value** belongs to neither loop — leave it untouched.

## ⚠️ Start every tick with the digest

**The first command of every tick is the board digest. Never hand-roll board or
comment queries — the digest is the only sanctioned way to see the board.**

```bash
.claude/skills/loop-common/scripts/board-tick.py --loop hitl   # or --loop auto
```

### Precondition: the GraphQL budget

A tick is a few dozen GitHub **GraphQL** requests — `gh project item-list`, every
`gh pr list`, and every hydration query all draw on the same 5000-point/hour
budget, and that budget is **shared by every agent and tool on the machine**, so
concurrent runs drain it together.

**A 17-item tick costs ~230 points** (measured: 4121 → 3893), so the practical
ceiling is roughly **20 ticks per hour across all agents**. Ticking in a tight
loop, or re-running the digest to debug it, will exhaust the hour.

The digest checks this itself before reading anything, and **refuses to start**
without headroom (`--min-budget`, default 400 points; `0` disables). If it hits
the wall mid-tick it aborts rather than printing a partial board, because a
half-read board is exactly the silent under-reporting the `TRUNCATED` warning
exists to prevent. Either way you get a banner naming the budget and the reset
time, and **exit code 75**:

```
══════════════════════════════════════════════════════════════════
 GITHUB GRAPHQL RATE LIMIT EXHAUSTED — NOTHING WAS READ
══════════════════════════════════════════════════════════════════
 graphql budget: 0/5000 · resets 2026-07-29 23:06 UTC (in 10m)
```

**A tick that hits this has seen nothing.** Do not pick up, skip, label or close
any task on the basis of it. Wait for the reset and re-run.

> **Diagnostic trap.** `gh` disguises this failure. A rate-limited
> `gh project item-list 6 --owner gaarutyunov` prints **`unknown owner type`** —
> which reads like a permissions or argument bug and is nothing of the kind.
> Before "fixing" any `gh` error, run `gh api rate_limit`. Never weaken or trim a
> query to make the error go away.
>
> Don't burn the budget on diagnostics either: `board-tick.py`'s logic is covered
> by `scripts/test_board_tick.py`, which uses fixtures and never calls the
> network. Verify against that, not by re-running live ticks.

One call (~7s) returns every **active** board item — everything except Backlog
and Done — with, for each one: its status, Loop routing, labels, the code PR,
**the spec PR**, CI, mergeability, unresolved review threads, staleness, and
**the full text of every owner comment that has not yet been acknowledged**.
Machine comments are classified out, so the digest is signal only.

The output is a decision table sorted by urgency, then a details block:

```
SIGNAL       TASK           STATUS       LOOP  LABELS  AGE  HUM   BOT  THR  PR   WORK   LOCAL  CI       MRG  SPEC
HUMAN-INPUT  site-review#2  In progress  hitl  -       4d   4·5d  1    -    #3   EMPTY  clean  ok       ok   #10:merged
UNPUSHED     workout#4      In progress  hitl  -       4d   -     -    -    #5   EMPTY  2c+3f  -        -    -
NOT-STARTED  boids#7        In progress  hitl  -       4d   -     -    -    -    -      -      -        -    -
```

- **`HUM`** — `count·age`: unaddressed owner comments, and how long the oldest
  has been waiting. The column that matters most. A trailing **`+N✎`** means N of
  them come from a review the owner never submitted (see *Unsubmitted reviews*).
- **`AGE`** — time since the last real activity (a comment or a pushed commit).
  Ledger writes deliberately don't count, so acking can't make a rotting task
  look fresh.
- **`WORK`** — what the PR actually contains: `8f` (8 changed files) or
  **`EMPTY`** for a PR holding nothing but the starter commit.
- **`LOCAL`** — work in the task's worktree that GitHub has never seen:
  `2c+3f` = 2 unpushed commits + 3 uncommitted files. `clean` = worktree exists
  and is in sync; `-` = no worktree on this machine.
- **`SPEC`** — the task's spec PR and its state.

Work the table top-down; the signals, in the order the digest sorts them (ties
broken by who has waited longest):

| Signal | Means | Do |
|---|---|---|
| `HUMAN-INPUT` | owner comments you have never acted on | read them, act, then **ack** |
| `PR-APPROVED` | owner applied `approved:pr` | merge (per the calling skill's gate) |
| `SPEC-APPROVED` | owner applied `approved:spec` | implement from `tasks.md` |
| `UNPUSHED` | work exists only in the local worktree | **push it first** — it is the only state that can lose work |
| `SPEC-MERGED` | spec PR merged but no work pushed | start implementing |
| `UNBLOCKED` | the blocker this task named has closed/merged | drop the `blocked` label and pick it up |
| `CI-RED` | checks failing, or the PR conflicts | fix |
| `THREADS` | unresolved review threads | address + resolve |
| `READY` | Ready and routed to this loop | pick it up |
| `NOT-STARTED` | In progress but nothing pushed | start (or restart) the work |
| `WIP` | In progress with pushed work, nothing new | continue it |
| `TRACKER` | legacy `tracker` label from before issues stopped being split | work the issue itself and drop the label |
| `WAITING-OWNER` | needs the owner, nothing new since | **skip** — do not touch |
| `BLOCKED` | blocked, and the blocker is confirmed still open this tick | **skip** — do not touch |

Rows also carry `⚠` **hygiene warnings** (a blocked task parked In progress, an
In-review task with no reason label, an In-progress task with nothing pushed).
Fix the hygiene problem in the same tick you see it.

A warning that fires on a healthy task is worse than no warning, because it
teaches the loop to skim past the `⚠` lines that *do* matter. So
`in review with no PR` stays silent whenever something already explains the
absent code PR: `needs:input` (a question is out), `blocked` (which gets its own,
stronger check — see *A `blocked` row is re-checked, not trusted*), or **an open spec PR plus
`needs:spec-approval`** — a spec-only task has no code PR *by design* until the
spec gate passes. It still fires for the case it was written for: In review, no
code PR, and nothing accounting for it.

There is one warning you must never rationalise away: **`TRUNCATED`**. Every
`first:`/`last:` in the digest's GraphQL fragments is a cap, and GraphQL raises no
error when one bites — it just returns fewer rows. That makes an under-reporting
tick indistinguishable from a quiet one, which is precisely how five owner
comments once stayed hidden for a day. So every capped connection is fetched with
its `totalCount` and any shortfall becomes a row-level warning:

```
⚠ TRUNCATED: spec PR #36 review threads returned 30 of 47 — 17 not seen by this
  tick; raise the cap in the GraphQL fragment before trusting this row
```

The row's `HUM`/`BOT`/`THR` counts are then **known to be incomplete**. Raise the
cap in the fragment and re-run before acting on that row — never treat the digest
as authoritative for a row carrying `TRUNCATED`.

### A `blocked` row is re-checked, not trusted

`blocked` is a *claim*, and claims go stale: the blocker merges, nobody notices,
and the row keeps ranking `BLOCKED` — which the loops read as "skip, do not
touch" — so it rots indefinitely. Two rows were sitting on already-closed
blockers when this check was written.

So every tick resolves what each blocked row is waiting on:

- The blocker is parsed from the **most recent comment naming it as
  `owner/repo#N`** (or the equivalent issue/PR URL), taken from *after* a blocker
  phrase — `blocked on`/`blocked by`/`waiting on`/`depends on`/`gating on`/
  `blocker:`. The phrase anchor is load-bearing: a real blocker comment also
  cites the blocker's own spec and code PRs, and those are usually *merged*, so a
  parser that grabbed any reference would report "cleared" on a live blocker.
- **Blocker closed or merged** → the row is signalled `UNBLOCKED` (actionable,
  ranked with `SPEC-MERGED`, well above `BLOCKED`) and carries a `⚠` naming the
  close date. Drop the `blocked` label and work it.
- **Blocker still open** → stays `BLOCKED`, with a quiet DETAILS line naming it,
  its state and its age. No `⚠` — nothing is wrong — but it is now visible and
  re-checkable every tick.
- **No parseable reference** → a `⚠`. A `blocked` label with no
  machine-readable blocker can never un-block itself, so it is a dead end by
  construction: state the blocker as `owner/repo#N` or drop the label.

**Write blocker comments so this works.** `**Blocked on gaarutyunov/ui-kit#7**,
which is …` parses; "waiting for the kit release" does not.

A blocked row now *always* appears in DETAILS. It is never a bare table line
with nothing to re-examine.

Cost: **one** batched GraphQL call per tick, deduplicated by blocker (N rows
waiting on the same thing cost one alias), and skipped entirely when nothing is
blocked. A lookup failure is reported on the row and never breaks the tick.

### An empty PR is a diagnosis, not a dead end

A PR with no changed files means a previous tick claimed the task and produced
nothing — but *why* matters, because one of the reasons is recoverable. The
digest checks the task's local checkout (`projects/<repo>/.worktrees/issue-<N>`,
and the base clone if it happens to sit on that branch) and tells you which case
you're in:

| `WORK` | `LOCAL` | What happened | Do |
|---|---|---|---|
| `EMPTY` | `2c+3f` | the run was stopped / ran out of context **after** editing | **push the work** — review the diff, commit, push |
| `EMPTY` | `clean` | interrupted before any edit landed | restart the work |
| `EMPTY` | `-` | no worktree on this machine either | restart from the issue + spec |
| `8f` | `2c+3f` | pushed work **plus** newer local edits | push the remainder before anything else |

Anything with local-only work is signalled **`UNPUSHED`** and ranks above CI
failures and review threads: it is the only state where effort can actually be
lost. The `⚠` warning names the worktree path and the exact counts.

The check is local and free (no API calls). Skip it with `--no-local`, or point
it elsewhere with `--projects-dir <path>` — useful when a tick runs on a
different machine from the one that did the work, where `LOCAL` is meaningless.

### The spec PR is fetched too

A task's spec lives in the **workspace** repo on a `spec…` branch naming the
task's repo and issue number — for every project task that is a *different repo*
from the issue, so nothing on the issue links to it. The digest resolves it by
branch name and pulls its comments, reviews and unresolved threads into the same
pool, tagged `spec`.

This matters: owner approvals and scope changes are routinely written on the
spec PR, and before this was wired the loop simply never saw them. Ack them like
any other comment (`--spec-comment <id>`, or `--all`).

**Branch matching is deliberately loose**, because a spec PR the digest fails to
recognise is a spec PR whose owner feedback is never read. All of these resolve:

| Branch | → |
|---|---|
| `spec/goga-1-framework-foundations` | goga#1 |
| `spec/ui-kit-6-workout-components` | ui-kit#6 |
| `spec/gopgql-issue-38` | gopgql#38 |
| `spec/gopgql-issue-9-m7-full-sdl-conformance` | gopgql#9 |
| `spec-ui-kit-6` | ui-kit#6 |

So: a `/` or `-` separator either way, an optional `issue` segment, and an
optional trailing slug after the number. The number is the **first** `-<digits>-`
run, so a slug that itself starts with digits can't steal the match. A number
that isn't separated from what follows it (`spec/goga-1abc`) stays unmatched
rather than being guessed at. `spec_branch_key` is covered by
`scripts/test_board_tick.py` — add a case there when a new naming style appears,
and run `python3 -m unittest` from `scripts/`.

### Unsubmitted reviews are read too

GitHub lets a reviewer write inline comments, never click **Submit review**, and
leave the review `PENDING` — its comments then appear in **no** ordinary
endpoint: not `GET /pulls/{n}/comments`, not `gh pr view --json comments,reviews`.
The owner usually has no idea the comments are invisible; from their side they
look written.

Because the loop and the owner post from the same GitHub account, the API *does*
hand us those drafts, so the digest fetches them (off the `reviews` connection it
already queries — no extra API call) for both the code PR and the spec PR. They
are folded into the same unaddressed-owner-comment pool as everything else: they
count in `HUM` (with the `+N✎` suffix), they rank the task `HUMAN-INPUT`, and they
print in DETAILS tagged **`[OWNER · DRAFT REVIEW · pending <id>]`** under a `⚠`
line naming the PR.

**Treat them as direction — they are real owner intent.** Ack them like any other
comment (`--pending-comment <id>`, or `--all`). When you reply, *say* the review
was never submitted, so the owner learns that their comments were invisible to
everyone else and can submit next time.

> A draft comment also shows up as an unresolved review thread. The digest counts
> the thread once and the comment once, and the draft tag wins — so `THR` and
> `HUM` don't double-report the same feedback.

Useful flags: `--repo <name>` to narrow, `--include-bots` to expand suppressed
machine comments, `--json` for the structured form, `--status <s>` to override
which statuses count as active.

## Comments: read → act → **ack**

**A comment is direction on its own. It needs no label.** The owner signals
disapproval, a scope change or an answer by *commenting* — labels are only how
approval arrives (`approved:spec` / `approved:pr`). So an unaddressed owner comment
makes a task actionable **even when it is labelled `needs:spec-approval` or
`needs:review`** and would otherwise read as "waiting on the owner". The digest
ranks such a task `HUMAN-INPUT`, above `WAITING-OWNER`, for exactly this reason —
never skip it because a waiting label is present.

Read the digest's **DETAILS section**, not just the summary table. The table's
`HUM` column is a count; the comment text lives below it. Truncating the digest
output (`| head`, `sed -n '1,20p'`) is how owner comments get missed.

The owner leaves direction as comments, and both the loop and the owner post from
the *same* GitHub account. Two mechanisms keep them apart:

1. **Every comment the loop writes carries an agent marker.** Post through the
   script so the marker is never forgotten:

   ```bash
   .claude/skills/loop-common/scripts/board-tick.py post \
     --repo <repo> --issue <N> --body "…"      # or --pr <PR#>, or --body - for stdin
   ```

   Never post loop output with a bare `gh issue comment` / `gh pr comment` — an
   unmarked comment will come back next tick as if the owner wrote it.

2. **Addressed comments are acked in a per-issue ledger.** The ledger is a
   single machine-managed comment on the issue (`<!-- loop-state:v1 -->`, a
   collapsed JSON block) listing the comment ids already handled. Acked comments
   are filtered out of every future digest — permanently. **After you act on the
   owner comments in a digest, ack them:**

   ```bash
   .claude/skills/loop-common/scripts/board-tick.py ack \
     --repo <repo> --issue <N> --all --note "restyled per comment; title changed"
   ```

   `--all` acks everything the digest currently shows for that task, across the
   issue, the code PR, the spec PR **and any unsubmitted review**. To ack
   selectively, pass
   `--issue-comment <id>` / `--pr-comment <id>` / `--review-comment <id>` /
   `--spec-comment <id>` / `--pending-comment <id>` (the ids are printed in the
   details block, after the `·` in each comment's header). Add
   `--dry-run` to see the ledger without writing it.

**An owner comment is never "read and skipped".** Either act on it and ack it,
or — if you decide not to act — reply on GitHub saying why, then ack. An
unacked comment will re-surface on every tick until one of those happens, which
is the point.

Unresolved **review threads** are their own ack channel: resolving the thread is
the ack (see *CodeRabbit + review threads*). Don't ack a review comment whose
thread is still open.

> **First tick on an old task:** issues worked before the marker existed have
> agent comments indistinguishable from owner comments, so the digest prints
> `⚠ no ack ledger yet`. Read that task's comments once, handle what's real, and
> `ack --all --note "baseline"`. From then on the ledger is authoritative.

## Labels carry every state the board can't

The board has five statuses and the owner only ever moves an item to **Ready**.
Everything else — every other status move, and every intermediate state — is the
loop's job, expressed as **labels on the issue**.

| Label | Set by | Meaning |
|---|---|---|
| `approved:spec` | **owner** | spec approved — implement it |
| `approved:pr` | **owner** | PR approved — merge it |
| `needs:spec-approval` | loop | spec PR open, waiting on the owner |
| `needs:review` | loop | code PR ready, waiting on the owner |
| `needs:input` | loop | a question is posted on the issue, waiting on the owner |
| `blocked` | loop | blocked by something external; the blocker is written on the issue |
| `tracker` | — | **deprecated** — see below |

Every loop label forces **In review**.

`tracker` is no longer set by either loop. It marked an issue that had been split
into sub-issues, and the loops no longer split issues: an issue is one deliverable
worked to merged in a single tick (`auto-loop` → *One issue, one deliverable*).
Existing `tracker` items are legacy — work the issue itself and drop the label
rather than treating it as a parent to skip.

```bash
.claude/skills/loop-common/scripts/board-tick.py label \
  --repo <repo> --issue <N> --add needs:review --remove needs:spec-approval
.claude/skills/loop-common/scripts/board-tick.py init-labels --repo <repo>   # first time in a repo
```

`label` creates any missing label with the right colour/description, and
**refuses to set `approved:*`** — those are the owner's alone.

Rules:

- **Never invent a new status.** If a state isn't one of the five, it's a label.
- Clear a `needs:*` label the moment it stops being true; leaving stale labels
  makes the digest lie.
- When the owner grants `approved:spec` / `approved:pr`, drop the matching
  `needs:*` label as you act on it.
- The owner is not expected to move anything out of **In review** — an approval
  label is the whole signal. **You** move the status.

## Interaction happens on GitHub, nowhere else

**Never ask the owner anything in the Claude Code window.** No `AskUserQuestion`,
no "should I…?" in the chat, no waiting on a reply in-session. A loop tick may
run unattended; a question asked in the terminal is a question nobody will ever
see.

When you need the owner — a decision, an approval, a credential, an answer:

1. Post the question on the **issue** with `board-tick.py post` (state the
   options and your recommendation, so a one-word reply is enough).
2. Add `needs:input`.
3. Move the item to **In review**.
4. Move on to the next task.

The answer arrives as an owner comment and reaches you as `HUMAN-INPUT` on a
later tick.

## The loop delegates: child agents do the work

**The loop orchestrates; it does not implement.** Every piece of research,
implementation, debugging and verification in a tick is done by a **child agent**
via the `Agent` tool. Doing the work in the loop's own context fills it with
file contents, build output and test logs, and a tick that runs out of context
loses everything it has not yet pushed.

What the loop keeps for itself, because it is protocol rather than work:

- running the digest and choosing the task
- board status moves, labels, and the comment ack ledger
- posting to the issue and the PR
- the merge gate

Everything else is dispatched.

### Write the instruction as if the agent knows nothing

A child agent starts with an empty context. It cannot see the digest, the issue,
this skill, or anything an earlier agent found. A one-line prompt produces
one-line work. Each dispatch names:

- **The task** — the issue number, title, and what "done" means for this piece.
- **Where** — the absolute worktree path, the branch, and the repo.
- **What to read first** — the exact `SPEC.md` sections, the issue body, prior
  decisions on the issue that constrain the answer.
- **The constraints that are not negotiable** — never `git add -A`; stage named
  paths and inspect `git diff --cached`; testify for assertions; generated
  uber-gomock for interface doubles, never hand-rolled; never create sub-issues;
  implement review feedback in place.
- **Acceptance** — the commands that must pass (`go test -race ./...`, a build, a
  named suite), and any spec clause the work is judged against.
- **What to report back** — the conclusion, the files touched, anything
  surprising, and any spec-versus-reality conflict found. Not a transcript.

Dispatch independent pieces **in parallel** in one message; they run
concurrently. Sequence only where one genuinely needs another's result.

### Trust, then verify

An agent's report is a claim, not evidence. "Tests pass" from a subagent is not
the merge gate — **green CI is** (`auto-loop`), or the owner is (`hitl-loop`).
Before acting on a report:

- re-run the digest rather than believing the board state it describes;
- check the pushed commits are what it says they are;
- treat a claim that something is impossible, blocked, or already done the way
  you would treat a `blocked` label: re-check it.

**Never paste an agent's output into the tick's report.** Relay the conclusion
and what it changes.

## One issue, one deliverable — never split an issue

**An issue is a deliverable unit of work.** Both loops take it from Ready to
merged; neither ever breaks it into sub-issues. This is not a sizing heuristic
with exceptions — there is no size and no blocker that justifies filing children
instead of shipping. Doing so is how the loop stops delivering: ticks end with
more backlog and nothing merged, and the real work vanishes behind labels later
ticks skip.

- **Never create sub-issues**, and never add new board items to break down work
  in hand. A big issue means a long tick, not a split.
- **Track the parts as a checklist in the issue body.** This is the tracking
  record — a GitHub task list on the issue itself, edited in with
  `gh issue edit <N> --repo gaarutyunov/<repo> --body-file -`:

  ```markdown
  ## Checklist
  - [ ] <part>
  - [ ] <part>
  ```

  Tick each box as its part lands, so the issue shows real progress to anyone
  reading it. **The issue is done only once the whole checklist is
  implemented** — an unchecked box means the issue is not finished, whatever
  the PR looks like.
- **Also keep a session todo list** (`TaskCreate` / `TaskUpdate`) to drive the
  tick. That is working state; the issue checklist is the durable record.
- **Spec-level decomposition is the only sanctioned kind.** An OpenSpec change's
  `tasks.md` breaks work into steps (see *OpenSpec `/opsx:*` spec flow*). That is
  task decomposition, not issue decomposition.
- **Implement every actionable review comment inside the issue being worked.**
  Owner feedback and valid bot findings get fixed in this PR — never deferred to
  a follow-up issue, unless the owner explicitly asks for it to be split out.
- **Clear technical blockers in the same PR.** Build the missing piece rather
  than filing it as foundation work for a later tick. Re-check any `blocked`
  claim before believing it — the thing it waited on has often merged since.

Only a blocker that genuinely needs the *owner* — a credential, an access grant,
a product decision nobody else can make — leaves the issue unfinished, and it
goes to **In review** as below.

## Anything that needs the owner sits in **In review**

**In review** means "this needs the owner". It is not only for finished code —
it is the single place the owner looks. A task belongs there the moment it is
waiting on a human, whatever the reason: review, spec approval, an answer, or a
blocker.

**Never leave a blocked task In progress.** *In progress* means the loop is
actively working it; a blocked task is not being worked, and parking it there
hides it from the owner and re-parks it every tick. When you discover a blocker:

1. Post the blocker on the issue with `board-tick.py post` — what is blocked,
   what it depends on, and what unblocks it. **Name the blocker as
   `owner/repo#N` directly after a blocker phrase**, e.g.
   `**Blocked on gaarutyunov/ui-kit#7**, which is …`. This is not a formatting
   preference: it is the only thing that lets every later tick re-check whether
   the blocker has cleared (see *A `blocked` row is re-checked, not trusted*).
   Prose like "waiting for the kit release" produces a dead end that can never
   un-block itself, and the digest will warn about it.
2. Add the `blocked` label.
3. Move the item to **In review**.
4. Pick up the next task.

The same applies to any partial work: push what you have, say what's outstanding
on the issue, label it, and move it to **In review** rather than leaving it
parked In progress.

## Select a task to work

Take it from the digest, not from a fresh board query. Work the first row whose
signal is actionable for your loop (`HUMAN-INPUT` → `PR-APPROVED` →
`SPEC-APPROVED` → `UNPUSHED` → `SPEC-MERGED` → `CI-RED` → `THREADS` →
`READY` → `NOT-STARTED` → `WIP`), skipping `WAITING-OWNER` and `BLOCKED`.
Capture the row's **item id** (printed in the details block), the **issue**
(repo + number), and the title.

A `READY` row is a new pickup: only rows whose `LOOP` column matches the calling
skill (`hitl` or `auto`) are yours — a Ready issue with `LOOP=-` belongs to
neither loop, leave it untouched. If nothing is actionable, stop (or idle until
the next tick when looping).

## Get the code repo ready (clone once, then a worktree per task)

The task's issue lives in some repo `gaarutyunov/<repo>`. Clone it **once** into
`projects/<repo>` — the base checkout stays on the default branch and is never
worked on directly; every task gets its own git worktree under
`projects/<repo>/.worktrees/<branch>`.

```bash
REPO=<repo>; N=<issue-number>
mkdir -p ~/Projects/workspace/projects        # projects/ may not exist yet
cd ~/Projects/workspace/projects

# Clone the base repo once and index it; keep .worktrees/ out of its git status.
if [ ! -d "$REPO" ]; then
  gh repo clone gaarutyunov/$REPO
  gortex track ~/Projects/workspace/projects/$REPO       # index the base clone
  grep -qxF '.worktrees/' "$REPO/.git/info/exclude" 2>/dev/null \
    || echo '.worktrees/' >> "$REPO/.git/info/exclude"
fi

# ALWAYS branch from fresh origin/<default> so a stale local main can't produce a
# broken branch. Resolve the real default branch (don't assume it's "main").
git -C "$REPO" fetch origin
DEF=$(gh repo view gaarutyunov/$REPO --json defaultBranchRef \
      --jq .defaultBranchRef.name)
git -C "$REPO" worktree add ".worktrees/issue-$N" -b "issue-$N" "origin/$DEF"

# gortex does NOT auto-index a worktree — register it explicitly as its own
# instance so the graph/MCP tools cover the code you're actually editing.
gortex track --as-worktree ~/Projects/workspace/projects/$REPO/.worktrees/issue-$N
```

**gortex tracking — worktrees are not picked up automatically.** gortex indexes
only paths it has been told to track. A worktree created under `.worktrees/` is
*untracked in the base repo*, so a plain `gortex track <repo>` does **not** reach
it (verified: the worktree's symbols never appear in the base repo's graph).
Register the base clone once with `gortex track <repo>` and **each worktree** with
`gortex track --as-worktree <worktree-path>`, so the graph/MCP code tools
(`search_symbols`, `find_usages`, `get_callers`, `smart_context`, …) can query
the code you're editing. Tracking indexes in the background; add `--wait`
(optionally `--wait-timeout 5m`) when you need the graph queryable before the
next step. Re-tracking an already-tracked path is a harmless no-op.

## Open a PR early

The worktree already created the `issue-<N>` branch from fresh `origin/<default>`.
From inside it, push an empty starter commit and open the PR early so there is a
place for CI and comments from the start:

```bash
cd ~/Projects/workspace/projects/<repo>/.worktrees/issue-<N>
git commit --allow-empty -m "Start work on #<N>"
git push -u origin issue-<N>
gh pr create --repo gaarutyunov/<repo> --fill \
  --title "<task title>" --body "Closes #<N>"
```

(An empty starter commit lets you open the PR early; squash/amend later.)

## Triage — spec-first vs implement-directly

Decide whether the task needs a spec:

- **Needs a spec (openspec)** when the work is *serious*: changing architecture,
  adding/altering public APIs, new functionality, or anything spanning multiple
  projects. Use [OpenSpec](https://github.com/Fission-AI/openspec) — it's
  initialized in this workspace repo (the `/opsx:*` commands and `openspec/`
  config are already present).
- **Implement directly** when it's a contained change: a bug fix, a small
  feature, docs, config, a self-evident tweak.

When unsure, lean toward a spec for anything a reviewer would want to agree on
*before* code is written. If the shape is still fuzzy, run `/opsx:explore` first.
(The two loops differ on whether the spec needs owner approval before you
implement — see each skill.)

## OpenSpec `/opsx:*` spec flow

Specs are authored in **this workspace repo** with OpenSpec, then land as a
**spec PR** in the workspace repo. `/opsx:*` commands run in the AI chat (not the
terminal) and write to `openspec/changes/<change>/`.

1. Create the change and its planning artifacts (proposal, specs, design, tasks)
   in one step:

   ```text
   /opsx:propose <repo>-issue-<N>-<slug>
   ```

   (Use `/opsx:update` to revise artifacts, `/opsx:explore` to think first.
   Kebab-case the change name.)

2. Open the spec PR from the generated artifacts:

   ```bash
   cd ~/Projects/workspace
   git checkout -b spec/<repo>-issue-<N>
   openspec validate <repo>-issue-<N>-<slug>     # sanity-check the change
   git add openspec/changes/<repo>-issue-<N>-<slug>
   git diff --cached                              # inspect before committing
   git commit -m "Spec for <repo>#<N>: <title>"
   git push -u origin spec/<repo>-issue-<N>
   gh pr create --repo gaarutyunov/workspace --fill \
     --title "Spec: <repo>#<N> <title>" --body "Spec for gaarutyunov/<repo>#<N>"
   ```

3. The spec PR merges per the calling skill's gate (owner-approved in `hitl-loop`,
   self-merged on green CI in `auto-loop`). Once it is merged, implement from the
   change's `tasks.md` with `/opsx:apply`, and after the work ships, finalize with
   `/opsx:archive` (moves it to `openspec/changes/archive/`).

## Commit / push discipline

Stage only the paths you intended to change — **never `git add -A`**, which can
sweep in unrelated local edits, generated files, or accidentally-present secrets.
Review the staged diff before committing:

```bash
git add <path> [<path> ...]     # the specific files for this task
git diff --cached               # inspect exactly what will be committed
git commit -m "<clear message>" # ref the issue/spec
git push
```

Ensure the PR is up to date and its body links the issue (`Closes #<N>`) and, if
applicable, the merged spec PR.

## Move a task's status

**Status moves are yours, not the owner's.** The owner only ever moves an item to
**Ready** (and applies `approved:*` labels). Every other transition — Ready → In
progress, In progress → In review, In review → In progress, → Done — is performed
by the loop. Don't wait for the owner to move anything, and don't ask them to.

```bash
gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id <ITEM_ID> \
  --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id <OPTION_ID>
```

Option ids are listed under **Board IDs** above (Backlog / Ready / In progress /
In review / Done). The `<ITEM_ID>` is the `item=PVTI_…` line in the digest's
details block.

Every move must leave the board honest:

- **In progress** — you are actively working it *right now* and nothing is
  waiting on the owner. Never park anything here.
- **In review** — waiting on the owner, for any reason. Always carries a
  `needs:*` or `blocked` label saying which.
- **Done** — merged and finished.

## CodeRabbit + review threads

CodeRabbit posts inline findings, each with a `🤖 Prompt for AI Agents` block
containing the exact fix. Pull them all with the bundled helper (its path is
under this skill now):

```bash
.claude/skills/loop-common/scripts/coderabbit-prompts.py gaarutyunov/<repo> <PR#>
```

**Verify each finding against the current code** — CodeRabbit is often right but
not always. Fix the still-valid ones (keep changes minimal); for any you judge
invalid, skip the code change but still reply with a brief reason.

> **If CodeRabbit's review limit is reached, ignore it.** When CodeRabbit posts a
> "review limit reached" / "rate limited" notice instead of an actual review (its
> status check can still show green — that's just the notice), there are no bot
> threads to work: treat this step as satisfied and don't block on it. Don't wait
> for or re-trigger the bot. (You *may* leave a `@coderabbitai review` comment for
> later, but never gate the merge on it.)

**Resolve every thread you address.** After fixing, reply to the thread
(reference the fixing commit) and resolve it; for a declined finding, reply with
the reason and resolve. A thread is resolved via the GraphQL `resolveReviewThread`
mutation (there is no REST endpoint):

```bash
# find thread ids + resolved state:
gh api graphql -f query='query { repository(owner:"gaarutyunov", name:"<repo>") {
  pullRequest(number: <PR#>) { reviewThreads(first:50) {
    nodes { id isResolved comments(first:1){ nodes { author{login} body } } } } } }'
# resolve one:
gh api graphql -f query='mutation { resolveReviewThread(input:{threadId:"<PRRT_...>"}) { thread { isResolved } } }'
```

Whether unresolved bot threads *block the merge* is the calling skill's call:
`hitl-loop` never merges with unresolved threads; `auto-loop` folds them in
opportunistically but does not gate on bots. Either way, **owner comments are
handled first** (see *Comments: read → act → ack* above).

Resolving a thread is what clears it from the digest's `THR` column — there is no
separate ack for review threads. Plain (non-threaded) bot comments on the PR are
suppressed from the digest body and counted in `BOT`; ack them like any other
comment once handled.
