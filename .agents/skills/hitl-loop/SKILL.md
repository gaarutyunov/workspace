---
name: hitl-loop
description: "Human-in-the-loop delivery loop: run the board-tick digest on the gaarutyunov GitHub Project board (project #6), work the highest-signal task routed to Loop=hitl, and take it through the full workflow (in progress → clone/worktree → branch + PR → triage → spec-or-implement → work → in review) with owner gates expressed as merges — waits for the owner to merge the spec PR before coding, and the owner merges the code PR to accept the work. All owner interaction happens on GitHub; never ask anything in the Claude Code window. Use when asked to work the task board with review gates. Examples: \"work on the next task\", \"pull a task from the board\", \"run the project loop\". For unattended runs that skip the gates and self-merge on green CI, use the auto-loop skill instead."
---

# HITL task loop

Drives tasks on the personal GitHub Project board
[users/gaarutyunov/projects/6](https://github.com/users/gaarutyunov/projects/6)
through delivery, one task at a time, **with owner gates**: the owner approves a
spec by merging its spec PR and accepts the work by merging the code PR, and the
loop does everything else. Run it once
for a single task, or drive it continuously with the `/loop` skill (see
**Looping**). For a fully autonomous variant that skips both gates and self-merges
once CI is green, use the **auto-loop** skill.

## Shared mechanics live in `loop-common`

The **board-tick digest**, the **label protocol**, the **comment ack ledger**,
**GitHub-only interaction**, the **blocked → In review** rule, board IDs,
clone/worktree + gortex tracking, opening a PR early, the OpenSpec `/opsx:*`
flow, commit/push discipline, status moves, and the `coderabbit-prompts.py`
helper are documented **once** in the `loop-common` skill — read
`.claude/skills/loop-common/SKILL.md`. This file specifies only what is
**specific to the human-gated path**: `Loop = hitl`, the spec-merge gate, and the
owner-merges-the-PR gate.

## Three rules that override everything else

1. **Start with the digest.** Never query the board or read comments by hand.
2. **Never ask the owner anything in the Claude Code window.** No
   `AskUserQuestion`, ever. Questions go on the issue, get `needs:input`, and the
   task moves to **In review**.
3. **Anything waiting on the owner lives in In review, with a label saying why.**
   Nothing blocked, nothing awaiting a merge, and nothing awaiting an answer is
   ever left In progress.
4. **Re-verify a `blocked` task's blocker every tick.** `blocked` is a claim about
   another issue or PR, and it goes stale silently — check that the blocker is
   still open before skipping the row, and unblock it the moment it isn't.

## The workflow (per tick)

### 1. Run the digest and choose one task

```bash
.claude/skills/loop-common/scripts/board-tick.py --loop hitl
```

Work the top actionable row, skipping `TRACKER`, `WAITING-OWNER` and `BLOCKED`.
The digest already contains every unaddressed owner comment for that task —
**including comments on its spec PR in the workspace repo**, where approvals and
scope changes usually live. Treat them as instructions that outrank the issue's
original text, and **ack them** once acted on (`loop-common` → *Comments: read →
act → ack*).

`UNPUSHED` outranks almost everything: work is sitting in the local worktree
that GitHub has never seen — review and push it before starting anything new.

`SPEC-MERGED` means the task is ready to be coded even without a fresh `Ready` —
the owner merged the spec PR and nothing has been pushed yet. (`SPEC-APPROVED`
survives only for a board that still carries the old `approved:spec` label.) `NOT-STARTED` means a previous tick claimed the task
and left nothing behind anywhere — restart it.

Fix any `⚠` hygiene warning on the row in this same tick (e.g. a blocked task
still sitting In progress → move it to In review).

If the chosen row is `READY`, move it to **In progress** (`47fc9ee4`). If it is
already in flight, leave the status alone until step 4.

### 2. Get the code repo ready, open a PR, triage

Follow `loop-common` verbatim: clone once into `projects/<repo>`, add a per-task
worktree from fresh `origin/<default>`, `gortex track` the base + worktree, run
`board-tick.py init-labels --repo <repo>` if the loop labels aren't there yet,
open the PR early with `--body "Closes #<N>"`, then triage **spec-first vs
implement-directly**.

### 3. Spec-first path — the spec-merge gate

Author the change with `loop-common`'s OpenSpec flow (`/opsx:propose …`) and open
the spec PR in this workspace repo. Then:

```bash
.claude/skills/loop-common/scripts/board-tick.py post --repo <repo> --issue <N> \
  --body "Spec ready for review: <spec PR url>. Merge it to approve, and implementation starts on the next tick; comment there if something should change."
.claude/skills/loop-common/scripts/board-tick.py label --repo <repo> --issue <N> --add needs:spec-approval
# then move the item to In review (df73e18b)
```

**Do not implement until the owner merges the spec PR.** The merge *is* the
approval — there is no `approved:spec` label to wait for, and the loop never
merges the spec PR itself. The task sits in **In review** with
`needs:spec-approval`, and the tick moves on to the next task rather than blocking
the loop. A later digest shows the task as `SPEC-MERGED`; at that point drop
`needs:spec-approval`, move the item back to **In progress**, and implement from
the change's `tasks.md` with `/opsx:apply` (`/opsx:archive` once it ships).

**Approval is a merge; rejection is just a comment.** The owner does *not* label a
spec they are unhappy with — they comment on the spec PR and expect the next tick
to act on it. A task labelled `needs:spec-approval` that has an unaddressed owner
comment is therefore **actionable, not waiting**: the digest ranks it
`HUMAN-INPUT`. Revise the spec, push, reply, ack, and leave it In review for the
gate. Never skip it as `WAITING-OWNER` because the label is still on.

For a direct task, skip straight to the work.

### 4. Perform the work, push, ask for review

Implement in the branch/worktree with tests where the project has them, keeping
`loop-common`'s commit/push discipline (**never `git add -A`**; stage specific
paths, inspect `git diff --cached`, ref the issue). Then, once the work is
**pushed** and the PR links the issue:

```bash
.claude/skills/loop-common/scripts/board-tick.py label --repo <repo> --issue <N> --add needs:review
# move the item to In review (df73e18b)
```

Never move to **In review** as "finished work awaiting review" until the work is
pushed. (Moving there because you're *blocked* or need an answer is different —
that's step 6, and it happens whenever it happens.)

Report: task title, code PR URL, spec PR URL (if any), and what was done.

### 5. The merge gate — **the owner merges**; you finish the card

**The loop never merges a code PR in this skill.** The owner reviews on GitHub and
presses Merge; that merge *is* the approval. There is no `approved:pr` label to
wait for and none to ask for.

So the task's last step is bookkeeping, triggered by a later digest showing
`PR-MERGED` (the code PR is merged while the item is not yet Done):

```bash
.claude/skills/loop-common/scripts/board-tick.py label --repo <repo> --issue <N> --remove needs:review
# move the item to Done (98236657)
```

Then `/opsx:archive` the change if there was a spec.

While the PR sits unmerged, keep it **mergeable and worth merging** — that is the
loop's job, not the owner's:

1. **Owner comments first.** The row's `HUM` count must be zero — act on every
   unaddressed owner comment and ack it. A comment is direction; it needs no
   label (`loop-common` → *Comments: read → act → ack*).
2. **Then CodeRabbit findings you judge valid**, via `loop-common`'s *CodeRabbit
   + review threads* section. If CodeRabbit's review limit is reached, ignore it.
3. **Resolve every thread** (`THR` must be `-`), and keep CI green (`CI=ok`) and
   the PR mergeable — a red or conflicting PR is the loop's problem to fix, and it
   surfaces as `CI-RED` regardless of any waiting label.

That difference from `auto-loop` still holds — `auto-loop` merges its own PRs;
here a human does — but the gate is a merge, never a label.

### 6. Blocked, or need an answer — surface it and move on

Whenever the task can't proceed — an external dependency, a missing credential,
an ambiguous requirement, a decision only the owner can make — do **not** park it
In progress and do **not** ask in the chat:

```bash
.claude/skills/loop-common/scripts/board-tick.py post --repo <repo> --issue <N> --body "$(cat <<'EOF'
**Blocked on <what>.**

<what is blocked, what it depends on (link the issue/PR), what unblocks it>

<if it's a question: the options, and which one I'd pick>
EOF
)"
.claude/skills/loop-common/scripts/board-tick.py label --repo <repo> --issue <N> --add blocked
# or --add needs:input for a question; then move the item to In review (df73e18b)
```

Push whatever partial work exists first so nothing is lost, then pick up the next
task in the digest.

## Looping

Drive continuously with the `/loop` skill (e.g. `/loop /hitl-loop` for
self-paced, or `/loop 15m …`). Each tick starts with the digest and handles one
task:

- Nothing actionable for `Loop = hitl` → do nothing and wait for the next tick.
- A task waiting on the owner (`WAITING-OWNER`, `BLOCKED`) is **skipped** — never
  re-worked, never re-commented. The ack ledger keeps it quiet until the owner
  responds.
- Never move a task to **In review** as finished work until its work is pushed.
- Never leave a blocked or owner-waiting task **In progress**.

## Related skills

- `loop-common` — the shared digest/label/ack/board mechanics this loop builds on.
- `auto-loop` — the unattended sibling that self-merges on green CI.
- `pet-project-metadata` — ensure a new/updated repo has the required metadata.
- `subdomain-setup` — publish the result at `<name>.garutyunov.com`.
- `ui-kit` — build the UI with the shared design system.
- `icon-generation` — generate the project/app icon.
