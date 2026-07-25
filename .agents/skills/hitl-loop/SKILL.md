---
name: hitl-loop
description: "Human-in-the-loop delivery loop: run the board-tick digest on the gaarutyunov GitHub Project board (project #6), work the highest-signal task routed to Loop=hitl, and take it through the full workflow (in progress → clone/worktree → branch + PR → triage → spec-or-implement → work → in review) with owner gates expressed as labels — waits for the `approved:spec` label before coding and the `approved:pr` label before merging. All owner interaction happens on GitHub; never ask anything in the Claude Code window. Use when asked to work the task board with review gates. Examples: \"work on the next task\", \"pull a task from the board\", \"run the project loop\". For unattended runs that skip the gates and self-merge on green CI, use the auto-loop skill instead."
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
**GitHub-only interaction**, the **blocked → In review** rule, board IDs,
clone/worktree + gortex tracking, opening a PR early, the OpenSpec `/opsx:*`
flow, commit/push discipline, status moves, and the `coderabbit-prompts.py`
helper are documented **once** in the `loop-common` skill — read
`.claude/skills/loop-common/SKILL.md`. This file specifies only what is
**specific to the human-gated path**: `Loop = hitl`, the `approved:spec` gate,
and the `approved:pr` merge gate.

## Three rules that override everything else

1. **Start with the digest.** Never query the board or read comments by hand.
2. **Never ask the owner anything in the Claude Code window.** No
   `AskUserQuestion`, ever. Questions go on the issue, get `needs:input`, and the
   task moves to **In review**.
3. **Anything waiting on the owner lives in In review, with a label saying why.**
   Nothing blocked, nothing awaiting approval, and nothing awaiting an answer is
   ever left In progress.

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

Two signals mean the task is ready to be coded even without a fresh `Ready`:
`SPEC-APPROVED` (owner labelled it) and `SPEC-MERGED` (the spec landed but
nothing has been pushed). `NOT-STARTED` means a previous tick claimed the task
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
and `/opsx:archive` the change if there was a spec.

**Never merge without `approved:pr`**, and never merge with unresolved threads or
red CI — that's the whole difference from `auto-loop`.

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
