---
name: loop-common
description: "Shared mechanics for the auto-loop and hitl-loop delivery skills: board discovery + IDs (gaarutyunov project #6), Ready-task selection, the always-read-comments rule, clone/worktree + gortex tracking, opening a PR early, the OpenSpec /opsx:* spec flow, commit/push discipline, and CodeRabbit + review-thread handling. NOT a standalone loop — it has no merge gate of its own; auto-loop and hitl-loop invoke it and add their own gates. Read it when running or editing either loop."
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

## Select a Ready task (parameterize by loop)

`gh project item-list` **defaults to 30 items** — pass a high `--limit` so a
Ready task past the first page isn't missed. The board also holds PRs and draft
items, so select only entries backed by a real **issue**, and only those routed
to the caller's loop. Substitute `LOOP` with `hitl` or `auto`:

```bash
LOOP=hitl   # or auto — set by the calling skill
gh project item-list 6 --owner gaarutyunov --format json --limit 200 \
  | python3 -c "import sys,json,os; L=os.environ['LOOP']; \
    items=json.load(sys.stdin)['items']; \
    r=[i for i in items if i.get('status')=='Ready' \
       and i.get('loop')==L \
       and i.get('content',{}).get('type')=='Issue']; \
    print(json.dumps(r[0] if r else {}, indent=2))"
```

Pick the top matching issue. Capture its **item id**, the linked **issue** (repo
+ number), and title. If there is no eligible item, stop (or idle until the next
tick when looping).

## ⚠️ Always read the comments (except Backlog / Done)

**Before you act on any task that is not in Backlog or Done — every time you pick
it up, resume it, work it, review it, move its status, or merge its PR — first
read the current comments on both the issue and its PR.** The owner leaves
direction and feedback as comments; a loop that skips them ships work the owner
already redirected, or re-merges over a change the owner asked for. This is the
single most common way the loop goes wrong.

Applies at **Ready, In progress, and In review** — i.e. any active task. Only
**Backlog** (not yet picked up) and **Done** (finished) are exempt. Read the
comments even when you *think* you already know the task: the owner may have
commented since the last tick.

Read, in this order, whatever exists for the task:

```bash
REPO=<repo>; N=<issue-number>; PR=<pr-number>   # PR only once one is open

# 1) Issue comments — owner direction on the task itself.
gh issue view "$N" --repo "gaarutyunov/$REPO" --comments

# 2) PR conversation comments — feedback on the open change.
[ -n "$PR" ] && gh pr view "$PR" --repo "gaarutyunov/$REPO" --comments

# 3) PR review threads (inline code comments + their resolved state).
[ -n "$PR" ] && gh api graphql -f query='query { repository(owner:"gaarutyunov", name:"'"$REPO"'") {
  pullRequest(number: '"$PR"') { reviewThreads(first:50) {
    nodes { isResolved comments(first:10){ nodes { author{login} body } } } } } }'
```

**Treat owner comments as instructions for the task**, ahead of the issue's
original text — if the owner narrowed the scope, changed the approach, or asked
for a fix in a comment, do that. Note anything you act on (or deliberately don't)
so the next tick doesn't re-litigate it. Bot comments (CodeRabbit) are handled
under **CodeRabbit + review threads** below; owner comments always come first.

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

```bash
gh project item-edit --project-id PVT_kwHOAjGWgc4Bcice --id <ITEM_ID> \
  --field-id PVTSSF_lAHOAjGWgc4BcicezhXKdRQ --single-select-option-id <OPTION_ID>
```

Option ids are listed under **Board IDs** above (Backlog / Ready / In progress /
In review / Done).

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
handled first** (see *Always read the comments* above).
