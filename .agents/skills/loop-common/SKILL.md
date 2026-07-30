---
name: loop-common
description: "Shared mechanics for the auto-loop and hitl-loop delivery skills: the rule that all work is delegated to child agents while the loop only orchestrates, the board-tick.py digest that starts every tick, the label protocol for intermediate states, the comment ack ledger, GitHub-only interaction (never AskUserQuestion), the Blocked-vs-In-review rule (Blocked = waiting on another issue, recorded as a native GitHub issue dependency so the digest signals UNBLOCKED the moment every blocker closes; In review = waiting on a human), the one-issue-one-deliverable rule (never split an issue into sub-issues), board IDs (gaarutyunov project #6, six statuses), clone/worktree + gortex tracking, opening a PR early, the OpenSpec /opsx:* spec flow, commit/push discipline, and CodeRabbit + review-thread handling. NOT a standalone loop — it has no merge gate of its own; auto-loop and hitl-loop invoke it and add their own gates. Read it when running or editing either loop."
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
- `.claude/skills/loop-common/scripts/board-tick.py` — the digest/ack/label/block
  tool every tick runs through. Python 3 stdlib only; shells out to `gh`. Run
  `board-tick.py init-labels --repo <repo>` once per repo the loops touch so the
  loop label set exists there. Its unit tests run in this repo's CI
  (`.github/workflows/ci.yml`), so a change to the script that breaks a signal or
  a column fails the PR — keep them passing when you edit it.

## Board IDs (project #6 "growth")

Stable — skip discovery unless the board schema changes:

- Project id: `PVT_kwHOAjGWgc4Bcice`
- Status field id: `PVTSSF_lAHOAjGWgc4BcicezhXKdRQ`
- Options: Backlog `f75ad846` · Ready `61e4505c` · In progress `47fc9ee4` ·
  In review `df73e18b` · **Blocked `8351b71b`** · Done `98236657`
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

One call (~7s) returns every **active** board item — everything except Backlog
and Done, so **Blocked** items appear in every digest too — with, for each one:
its status, Loop routing, labels, the code PR, **the spec PR**, CI,
mergeability, unresolved review threads, its open/closed blockers, staleness,
and **the full text of every owner comment that has not yet been acknowledged**.
Machine comments are classified out, so the digest is signal only.

The output is a decision table sorted by urgency, then a details block:

```
SIGNAL       TASK           STATUS       LOOP  LABELS   AGE  HUM   BOT  THR  BLK   PR  WORK   LOCAL  CI  MRG  SPEC
HUMAN-INPUT  site-review#2  In progress  hitl  -        4d   4·5d  1    -    -     #3  EMPTY  clean  ok  ok   #10:merged
UNBLOCKED    gopgql#9       Blocked      auto  BLOCKED  2d   -     -    -    1/1✓  #8  12f    clean  ok  ok   #29:merged
UNPUSHED     workout#4      In progress  hitl  -        4d   -     -    -    -     #5  EMPTY  2c+3f  -   -    -
BLOCKED      sysgo#67       Blocked      auto  BLOCKED  6d   -     -    -    0/2   -   -      -      -   -    -
```

- **`HUM`** — `count·age`: unaddressed owner comments, and how long the oldest
  has been waiting. The column that matters most.
- **`AGE`** — time since the last real activity (a comment or a pushed commit).
  Ledger writes deliberately don't count, so acking can't make a rotting task
  look fresh.
- **`BLK`** — `closed/total` of the issue's recorded blockers, read from GitHub's
  native `blockedBy` dependencies. A trailing **`✓`** means every blocker has
  closed, so the task is free to move again; `0/2` means two are still open.
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
| `UNBLOCKED` | marked blocked, but **every** blocker has now closed | **pick it up** — `unblock`, move it back to Ready, work it |
| `PR-APPROVED` | owner applied `approved:pr` | merge (per the calling skill's gate) |
| `SPEC-APPROVED` | owner applied `approved:spec` | implement from `tasks.md` |
| `UNPUSHED` | work exists only in the local worktree | **push it first** — it is the only state that can lose work |
| `SPEC-MERGED` | spec PR merged but no work pushed | start implementing |
| `CI-RED` | checks failing, or the PR conflicts | fix |
| `THREADS` | unresolved review threads | address + resolve |
| `READY` | Ready and routed to this loop | pick it up |
| `NOT-STARTED` | In progress but nothing pushed | start (or restart) the work |
| `WIP` | In progress with pushed work, nothing new | continue it |
| `TRACKER` | legacy `tracker` label from before issues stopped being split | work the issue itself and drop the label |
| `BLOCKED` | at least one blocker is **still open** | **skip** — do not touch |
| `WAITING-OWNER` | needs the owner, nothing new since | **skip** — do not touch |

`UNBLOCKED` and `BLOCKED` are the two halves of one state, split on a fact the
digest can check: whether any `blockedBy` issue is still open. Only the
open-blocker half is a skip. The all-closed half is **work waiting to be picked
up**, which is why it ranks second, immediately below `HUMAN-INPUT` — a blocker
that cleared while nobody was looking used to be how a task sat forgotten for
days.

Rows also carry `⚠` **hygiene warnings**, each naming the command that fixes it:

- a task carrying `needs:*` parked In progress → move it to In review;
- **Blocked** with no recorded blocker → record one with `board-tick.py block`,
  or move it out of Blocked;
- the legacy `blocked` label with some other status → record the dependency and
  move it to **Blocked**;
- **every blocker closed** → move it to Ready;
- open blockers but *not* marked blocked → move it to Blocked, or drop the
  dependency with `board-tick.py unblock`;
- an In-review task with no reason label, and an In-progress task with nothing
  pushed.

Fix the hygiene problem in the same tick you see it.

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

A task's spec lives in the **workspace** repo on `spec/<repo>-issue-<N>` — for
every project task that is a *different repo* from the issue, so nothing on the
issue links to it. The digest resolves it by branch name and pulls its comments,
reviews and unresolved threads into the same pool, tagged `spec`.

This matters: owner approvals and scope changes are routinely written on the
spec PR, and before this was wired the loop simply never saw them. Ack them like
any other comment (`--spec-comment <id>`, or `--all`).

Useful flags: `--repo <name>` to narrow, `--include-bots` to expand suppressed
machine comments, `--json` for the structured form, `--status <s>` to override
which statuses count as active. The default active set includes **Blocked** —
if you pass `--status` you replace that set wholesale, so a hand-rolled list
that omits `Blocked` hides every blocked item from the digest. Don't.

## Comments: read → act → **ack**

**A comment is direction on its own. It needs no label.** The owner signals
disapproval, a scope change or an answer by *commenting* — labels are only how
approval arrives (`approved:spec` / `approved:pr`). So an unaddressed owner comment
makes a task actionable **even when it is labelled `needs:spec-approval` or
`needs:review`** and would otherwise read as "waiting on the owner". The digest
ranks such a task `HUMAN-INPUT`, above `WAITING-OWNER` and `BLOCKED`, for exactly
this reason — never skip it because a waiting label or a blocker is present.

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
   issue, the code PR **and the spec PR**. To ack selectively, pass
   `--issue-comment <id>` / `--pr-comment <id>` / `--review-comment <id>` /
   `--spec-comment <id>` (the ids are printed in the details block). Add
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

The board has six statuses and the owner only ever moves an item to **Ready**.
Everything else — every other status move, and every state finer-grained than a
status — is the loop's job, expressed as **labels on the issue**.

| Label | Set by | Meaning |
|---|---|---|
| `approved:spec` | **owner** | spec approved — implement it |
| `approved:pr` | **owner** | PR approved — merge it |
| `needs:spec-approval` | loop | spec PR open, waiting on the owner |
| `needs:review` | loop | code PR ready, waiting on the owner |
| `needs:input` | loop | a question is posted on the issue, waiting on the owner |
| `blocked` | loop | blocked by another issue; the blocker is recorded as a GitHub issue dependency |
| `tracker` | — | **deprecated** — see below |

Every `needs:*` label forces **In review**; `blocked` forces **Blocked**.

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

- **The status set is fixed at these six.** Backlog, Ready, In progress, In
  review, Blocked, Done — if a state isn't one of them, it's a label. Adding a
  seventh is not a call you make mid-tick: `Blocked` earned its place through
  its own issue (workspace#38), and any future status needs the same.
- Clear a `needs:*` or `blocked` label the moment it stops being true; leaving
  stale labels makes the digest lie.
- When the owner grants `approved:spec` / `approved:pr`, drop the matching
  `needs:*` label as you act on it.
- The owner is not expected to move anything out of **In review** or **Blocked** —
  an approval label, an answer, or the blocking issue closing is the whole
  signal. **You** move the status.

## Interaction happens on GitHub, nowhere else

**Never ask the owner anything in the Claude Code window.** No `AskUserQuestion`,
no "should I…?" in the chat, no waiting on a reply in-session. A loop tick may
run unattended; a question asked in the terminal is a question nobody will ever
see.

When you need the owner — a decision, an approval, a credential, an answer:

1. Post the question on the **issue** with `board-tick.py post` (state the
   options and your recommendation, so a one-word reply is enough).
2. Add `needs:input`.
3. Move the item to **In review** — a question is a *human* need, so it is never
   **Blocked**, which means "waiting on another issue" and nothing else.
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
  you would treat a `blocked` label: re-check it. For a blocker this is now
  mechanical — the digest reads the issue's `blockedBy` dependencies and signals
  `UNBLOCKED` once they have all closed, so a prose claim that contradicts the
  digest is simply wrong.

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
  claim before believing it — the thing it waited on has often merged since, and
  the digest's `BLK` column tells you outright.

Only two things leave the issue unfinished: a blocker that genuinely needs the
*owner* — a credential, an access grant, a product decision nobody else can make —
which goes to **In review**, and a genuine dependency on *another issue*, which
goes to **Blocked**. Both are covered below.

## Waiting on a human → **In review**; waiting on another issue → **Blocked**

**Blocked = waiting on another issue. In review = waiting on a human.** That is
the whole rule, and the test is who has to act next: if a *person* has to read,
decide, approve, answer or supply something, it is **In review**; if the only
thing in the way is *another issue* getting finished, it is **Blocked**.

**Never leave either one In progress.** *In progress* means the loop is actively
working it right now. A task that is waiting is not being worked, and parking it
there hides it and re-parks it every tick.

### Waiting on a human → **In review**

Review, spec approval, an answer, a credential, an access grant, a product
decision nobody else can make. **In review** is the single place the owner looks,
and it is not only for finished code:

1. Post what you need on the issue with `board-tick.py post` — the options and
   your recommendation, so a one-word reply is enough.
2. Add the matching `needs:*` label (`needs:review`, `needs:spec-approval`,
   `needs:input`).
3. Move the item to **In review** (`df73e18b`).
4. Pick up the next task.

### Waiting on another issue → **Blocked**

The blocker is **recorded as a GitHub issue dependency**, not described in prose.
A blocker written only in a comment is invisible to the digest, which is exactly
how one got written down and then forgotten for days:

1. Record it — this writes the native `blockedBy` edge, adds the `blocked`
   label, posts the note as a marked comment, and prints the status-move command:

   ```bash
   .claude/skills/loop-common/scripts/board-tick.py block \
     --repo <repo> --issue <N> --on <ref> --note "<what is blocked, and why>"
   ```

   A `<ref>` is `123`, `repo#123` or `owner/repo#123`; repeat `--on` for several
   blockers. `--dry-run` prints the GraphQL and sends nothing.
2. Run the printed command to move the item to **Blocked** (`8351b71b`).
3. Push whatever partial work exists so nothing is lost.
4. Pick up the next task.

Because the dependency is a real edge, the digest tracks it for you: `BLK` shows
`closed/total`, and the moment the last blocker closes the row becomes
`UNBLOCKED` — actionable, and never quietly suppressed. To clear it:

```bash
.claude/skills/loop-common/scripts/board-tick.py unblock --repo <repo> --issue <N>
```

With no `--on` this drops exactly the dependencies that have **closed** and never
an open one, removes the `blocked` label, and prints the command to move the item
back to **Ready** (`61e4505c`). Then work it.

### **Blocked** is not a parking space

It means one specific thing: **another issue must land first.** It is not a
polite way to end a tick early, and the anti-parking rules lose none of their
force because it exists:

- **A blocker you could clear yourself is not a blocker.** Build the missing
  piece in this PR (*One issue, one deliverable* above). A technical gap, a
  missing helper, an absent foundation — that is the deliverable, not a
  dependency.
- **Size is not a blocker,** and neither is a test you haven't finished
  debugging. Large means a long tick.
- **A human need is never Blocked.** It is In review, with a `needs:*` label.

Partial work follows the same discipline either way: push what you have, say
what's outstanding on the issue, label it, and move it to **In review** or
**Blocked** rather than leaving it parked In progress.

## Select a task to work

Take it from the digest, not from a fresh board query. Work the first row whose
signal is actionable for your loop (`HUMAN-INPUT` → `UNBLOCKED` → `PR-APPROVED` →
`SPEC-APPROVED` → `UNPUSHED` → `SPEC-MERGED` → `CI-RED` → `THREADS` →
`READY` → `NOT-STARTED` → `WIP`), skipping `WAITING-OWNER` and `BLOCKED`.
`UNBLOCKED` is actionable, not a skip — its blockers have all closed.
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
progress, In progress → In review, In progress → Blocked, In review → In progress,
Blocked → Ready, → Done — is performed by the loop. Don't wait for the owner to
move anything, and don't ask them to.

```bash
gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id <ITEM_ID> \
  --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id <OPTION_ID>
```

Option ids are listed under **Board IDs** above (Backlog / Ready / In progress /
In review / Blocked / Done). The `<ITEM_ID>` is the `item=PVTI_…` line in the
digest's details block.

Every move must leave the board honest:

- **In progress** — you are actively working it *right now*, and nothing is
  waiting on a human or on another issue. Never park anything here.
- **In review** — waiting on a *human*, for any reason. Always carries a
  `needs:*` label saying which.
- **Blocked** — waiting on *another issue*, and on nothing else. Always carries
  the `blocked` label **and** a native GitHub issue dependency naming the
  blocker, so the digest can tell when it clears. Never use it for work you
  simply haven't done.
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
