---
name: hitl-loop
description: "Human-in-the-loop delivery loop: run the board-tick digest on the gaarutyunov GitHub Project board (project #6), work the highest-signal task routed to Loop=hitl, and take it through the full workflow (in progress → clone/worktree → branch + PR → triage → spec-or-implement → work → in review) with owner gates expressed as labels — waits for the `approved:spec` label before coding and the `approved:pr` label before merging. In review is reserved for waiting on a human; a task waiting on another issue goes to the Blocked status with that issue recorded as a native GitHub dependency. All owner interaction happens on GitHub; never ask anything in the Claude Code window. Use when asked to work the task board with review gates. Examples: \"work on the next task\", \"pull a task from the board\", \"run the project loop\". For unattended runs that skip the gates and self-merge on green CI, use the auto-loop skill instead."
---

# HITL task loop

Drives tasks on the personal GitHub Project board
[users/gaarutyunov/projects/6](https://github.com/users/gaarutyunov/projects/6)
through delivery, one task at a time, **with owner gates**: the owner approves
specs and PRs by applying a label, and the loop does everything else. Run it once
for a single task, or drive it continuously with the `/loop` skill (see
**Looping**). For a fully autonomous variant that skips both gates and self-merges
once CI is green, use the **auto-loop** skill.

## Shared mechanics live in `loop-common`

The **board-tick digest**, the **label protocol**, the **comment ack ledger**,
**GitHub-only interaction**, the **Blocked vs In review** rule, board IDs,
clone/worktree + gortex tracking, opening a PR early, the OpenSpec `/opsx:*`
flow, commit/push discipline, status moves, and the `coderabbit-prompts.py`
helper are documented **once** in the `loop-common` skill — read
`.claude/skills/loop-common/SKILL.md`. This file specifies only what is
**specific to the human-gated path**: `Loop = hitl`, the `approved:spec` gate,
and the `approved:pr` merge gate.

## Five rules that override everything else

1. **Start with the digest.** Never query the board or read comments by hand.
2. **Never ask the owner anything in the Claude Code window.** No
   `AskUserQuestion`, ever. Questions go on the issue, get `needs:input`, and the
   task moves to **In review**.
3. **Anything waiting on a human lives in In review, with a label saying why;
   anything waiting on another issue lives in Blocked.** Nothing awaiting
   approval, an answer or a review, and nothing waiting on another issue, is ever
   left In progress.
4. **Never split an issue into sub-issues.** Each issue is one deliverable, worked
   in place. Track its parts as a **checklist in the issue body** — the issue is
   done only once the whole checklist is implemented — and decompose only at the
   spec level (`loop-common` → *One issue, one deliverable*). Every actionable
   review comment is implemented inside the issue being worked, never deferred.

5. **Never do the work yourself.** Research, implementation, debugging and
   verification are dispatched to **child agents** with detailed, self-contained
   instructions (`loop-common` → *The loop delegates*). The loop runs the digest,
   picks the task, moves the board, talks to the owner and holds the gates —
   nothing else.

## The workflow (per tick)

### 1. Run the digest and choose one task

```bash
.claude/skills/loop-common/scripts/board-tick.py --loop hitl
```

Work the top actionable row, skipping `WAITING-OWNER`, `BLOCKED` and
`BLOCKED-UNRECORDED` — but **not** `UNBLOCKED`, which ranks second and *is*
actionable: every blocker it recorded has closed (`BLK` reads `n/n✓`), so run
`board-tick.py unblock --repo <repo> --issue <N>`, move it back to **Ready**
(`61e4505c`) and work it.

`BLOCKED-UNRECORDED` is a skip *for pickup*, but not something to leave alone: it
means the item is flagged blocked with no dependency recorded, so no tick can
ever tell when it clears. Fix the bookkeeping in this tick — record the blocker
with `board-tick.py block --repo <repo> --issue <N> --on <ref>`, or move the item
out of Blocked — then carry on to the next row.
The digest already contains every unaddressed owner comment for that task —
**including comments on its spec PR in the workspace repo**, where approvals and
scope changes usually live. Treat them as instructions that outrank the issue's
original text, and **ack them** once acted on (`loop-common` → *Comments: read →
act → ack*).

`UNPUSHED` outranks almost everything: work is sitting in the local worktree
that GitHub has never seen — review and push it before starting anything new.

Two signals mean the task is ready to be coded even without a fresh `Ready`:
`SPEC-APPROVED` (owner labelled it) and `SPEC-MERGED` (the spec landed but
nothing has been pushed). `NOT-STARTED` means a previous tick claimed the task
and left nothing behind anywhere — restart it.

Fix any `⚠` hygiene warning on the row in this same tick (e.g. a task carrying
`blocked` that is still sitting In progress → move it to **Blocked**, or one
carrying `needs:*` → move it to **In review**).

If the chosen row is `READY`, move it to **In progress** (`47fc9ee4`). If it is
already in flight, leave the status alone until step 4.

### 2. Get the code repo ready, open a PR, triage

Follow `loop-common` verbatim: clone once into `projects/<repo>`, add a per-task
worktree from fresh `origin/<default>`, `gortex track` the base + worktree, run
`board-tick.py init-labels --repo <repo>` if the loop labels aren't there yet,
open the PR early with `--body "Closes #<N>"`, then triage **spec-first vs
implement-directly**.

### 3. Spec-first path — the `approved:spec` gate

Author the change with `loop-common`'s OpenSpec flow (`/opsx:propose …`) and open
the spec PR in this workspace repo. Then:

```bash
.claude/skills/loop-common/scripts/board-tick.py post --repo <repo> --issue <N> \
  --body "Spec ready for approval: <spec PR url>. Add the \`approved:spec\` label to this issue to start implementation."
.claude/skills/loop-common/scripts/board-tick.py label --repo <repo> --issue <N> --add needs:spec-approval
# then move the item to In review (df73e18b)
```

**Do not implement until the owner applies `approved:spec`.** This is a hard
gate: the task sits in **In review** with `needs:spec-approval`, and the tick
moves on to the next task rather than blocking the loop. A later digest shows the
task as `SPEC-APPROVED`; at that point merge the spec PR, drop
`needs:spec-approval`, move the item back to **In progress**, and implement from
the change's `tasks.md` with `/opsx:apply` (`/opsx:archive` once it ships).

**Approval is a label; rejection is just a comment.** The owner does *not* label a
spec they are unhappy with — they comment on the spec PR and expect the next tick
to act on it. A task labelled `needs:spec-approval` that has an unaddressed owner
comment is therefore **actionable, not waiting**: the digest ranks it
`HUMAN-INPUT`. Revise the spec, push, reply, ack, and leave it In review for the
gate. Never skip it as `WAITING-OWNER` — or as `BLOCKED` — because the label is
still on.

For a direct task, skip straight to the work.

### 4. Dispatch the work, check it, ask for review

**The work is done by child agents, not by this loop** (`loop-common` → *The loop
delegates*). Break the checklist into independently workable pieces, dispatch
them in parallel in one message, and give each the worktree path, the spec
sections to read, the non-negotiable constraints (**never `git add -A`**; stage
named paths, inspect `git diff --cached`, ref the issue; testify; generated
gomock; no sub-issues), the acceptance commands and what to report back.

Check what comes back rather than believing it — confirm the commits exist and
hold what was claimed. Then, once the work is **pushed** and the PR links the
issue:

```bash
.claude/skills/loop-common/scripts/board-tick.py label --repo <repo> --issue <N> --add needs:review
# move the item to In review (df73e18b)
```

Never move to **In review** as "finished work awaiting review" until the work is
pushed. (Moving to **In review** because you need an answer, or to **Blocked**
because another issue is in the way, is different — that's step 6, and it happens
whenever it happens.)

Report: task title, code PR URL, spec PR URL (if any), and what was done.

### 5. The `approved:pr` merge gate — owner approves, **you** merge

A later digest shows the task as `PR-APPROVED` once the owner adds the
`approved:pr` label. The owner approves; the loop performs the merge and the
status move — the owner is never expected to press Merge or move the card.
Before merging:

1. **Owner comments first.** The row's `HUM` count must be zero — act on every
   unaddressed owner comment and ack it.
2. **Then CodeRabbit findings you judge valid**, via `loop-common`'s *CodeRabbit
   + review threads* section. If CodeRabbit's review limit is reached, ignore it.
3. **Resolve every thread** (`THR` must be `-`), and confirm CI is green
   (`CI=ok`) and the PR is mergeable.

Only then:

```bash
gh pr merge <PR#> --repo gaarutyunov/<repo> --squash
```

Then drop `needs:review` / `approved:pr`, move the item to **Done** (`98236657`),
and `/opsx:archive` the change if there was a spec. If the task ever carried a
recorded blocker, clear the dependency too (`board-tick.py unblock --repo <repo>
--issue <N>`) so a finished issue leaves no stale edge behind.

**Never merge without `approved:pr`**, and never merge with unresolved threads or
red CI — that's the whole difference from `auto-loop`.

### 6. Can't proceed — surface it and move on

Whenever the task can't proceed, do **not** park it In progress and do **not** ask
in the chat. Which status it goes to depends on **who has to act next**
(`loop-common` → *Waiting on a human → In review; waiting on another issue →
Blocked*).

**Waiting on a human** — a missing credential, an ambiguous requirement, a
decision only the owner can make:

```bash
.claude/skills/loop-common/scripts/board-tick.py post --repo <repo> --issue <N> --body "$(cat <<'EOF'
**Need a decision on <what>.**

<what is stuck, and why only the owner can settle it>

<the options, and which one I'd pick>
EOF
)"
.claude/skills/loop-common/scripts/board-tick.py label --repo <repo> --issue <N> --add needs:input
# then move the item to In review (df73e18b)
```

**Waiting on another issue** — that issue has to land before this one can be
finished. Record it as a real dependency rather than describing it in a comment,
so the digest can tell you the moment it clears:

```bash
.claude/skills/loop-common/scripts/board-tick.py block \
  --repo <repo> --issue <N> --on <ref> --note "<what is blocked, and why>"
# then move the item to Blocked (8351b71b) — the command is printed for you
```

A `<ref>` is `123`, `repo#123` or `owner/repo#123`; repeat `--on` for several
blockers. A later digest shows the task as `UNBLOCKED` once they have all closed.

**Neither is a way to shed work.** A blocker you could clear yourself belongs in
this PR, not in **Blocked** (`loop-common` → *One issue, one deliverable*), and a
human need is always **In review**, never **Blocked**.

Push whatever partial work exists first so nothing is lost, then pick up the next
task in the digest.

## Looping

Drive continuously with the `/loop` skill (e.g. `/loop /hitl-loop` for
self-paced, or `/loop 15m …`). Each tick starts with the digest and handles one
task:

- Nothing actionable for `Loop = hitl` → do nothing and wait for the next tick.
- A task waiting on the owner (`WAITING-OWNER`) or on a still-open blocker
  (`BLOCKED`) is **skipped** — never re-worked, never re-commented. The ack ledger
  keeps it quiet until the owner responds.
- `BLOCKED-UNRECORDED` is skipped for pickup too, but its bookkeeping is fixed on
  the spot: record the blocker, or move the item out of Blocked.
- `UNBLOCKED` is **not** in either group: it recorded blockers and every one of
  them has closed, so it is a pickup, not a skip. Never leave one sitting.
- Never move a task to **In review** as finished work until its work is pushed.
- Never leave a task **In progress** when it is waiting on a human (→ In review)
  or on another issue (→ Blocked).

## Related skills

- `loop-common` — the shared digest/label/ack/board mechanics this loop builds on.
- `auto-loop` — the unattended sibling that self-merges on green CI.
- `pet-project-metadata` — ensure a new/updated repo has the required metadata.
- `subdomain-setup` — publish the result at `<name>.garutyunov.com`.
- `ui-kit` — build the UI with the shared design system.
- `icon-generation` — generate the project/app icon.
