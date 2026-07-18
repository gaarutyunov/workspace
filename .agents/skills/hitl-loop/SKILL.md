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

## Prerequisites

- `gh` authenticated. **Projects v2 needs the `project` (or `read:project`)
  scope**, which is *not* in the default token here. Add it once:
  `gh auth refresh -s project`. Without it, `gh project …` returns
  `authentication token is missing required scopes [read:project]`.
- The workspace repo (this repo) is the home for **specs** — OpenSpec is
  initialized here (`/opsx:*` commands + `openspec/`). Pet-project code repos are
  cloned under `projects/` (gitignored) or worked via git worktree.
- Board Status values used below: **Ready**, **In progress**, **In review**
  (confirm exact option names/ids with the field query in step 1).

## Discover the board (one-time per session)

```bash
OWNER=gaarutyunov
PROJ=6
# Project id + Status field id and its option ids:
gh project field-list $PROJ --owner $OWNER --format json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
    [print(f['id'], f['name'], [(o['id'],o['name']) for o in f.get('options',[])]) \
     for f in d['fields'] if f['name']=='Status']"
gh project view $PROJ --owner $OWNER --format json --jq '.id'   # project node id
```

Keep the project id, Status field id, and the option ids for **Ready /
In progress / In review**.

> **Confirmed values for project #6 ("growth")** — stable, so you can skip
> discovery unless the board schema changes:
>
> - Project id: `PVT_kwHOAjGWgc4Bcice`
> - Status field id: `PVTSSF_lAHOAjGWgc4BcicezhXKdRQ`
> - Options: Backlog `f75ad846` · Ready `61e4505c` · In progress `47fc9ee4` ·
>   In review `df73e18b` · Done `98236657`
> - **Loop field id: `PVTSSF_lAHOAjGWgc4BcicezhYRXrw`** · options: hitl
>   `d03523f4` · auto `ee15c5cc`

The **Loop** field routes each task to exactly one loop: this skill only handles
items with **Loop = `hitl`**; `auto`-marked items belong to the `auto-loop`
skill. In the item-list JSON the value appears under the top-level `loop` key.

## The workflow (per task)

### 1. Get a task from **Ready** marked **Loop = hitl**

`gh project item-list` **defaults to 30 items** — pass a high `--limit` so a
Ready task past the first page isn't missed. The board also holds PRs and draft
items, so select only entries backed by a real **issue**, and only those routed
to this loop (**`loop == 'hitl'`**):

```bash
gh project item-list $PROJ --owner $OWNER --format json --limit 200 \
  | python3 -c "import sys,json; \
    items=json.load(sys.stdin)['items']; \
    r=[i for i in items if i.get('status')=='Ready' \
       and i.get('loop')=='hitl' \
       and i.get('content',{}).get('type')=='Issue']; \
    print(json.dumps(r[0] if r else {}, indent=2))"
```

Pick the top matching issue. Capture its **item id**, the linked **issue** (repo
+ number), and title. If there is no eligible item, stop. A Ready issue with **no
Loop value** (or `Loop = auto`) is **not** this loop's to take — leave it
untouched.

### 2. Move it to **In progress**

```bash
gh project item-edit --project-id <PROJECT_ID> --id <ITEM_ID> \
  --field-id <STATUS_FIELD_ID> --single-select-option-id <IN_PROGRESS_OPTION_ID>
```

### 3. Get the code repo ready (clone or worktree)

The task's issue lives in some repo `gaarutyunov/<repo>`.

```bash
REPO=<repo>; N=<issue-number>
mkdir -p ~/Projects/workspace/projects        # projects/ may not exist yet
cd ~/Projects/workspace/projects
if [ ! -d "$REPO" ]; then
  gh repo clone gaarutyunov/$REPO
else
  # already cloned — use a worktree so the main checkout is untouched.
  # Resolve the repo's real default branch (don't assume it's "main").
  git -C "$REPO" fetch origin
  DEF=$(gh repo view gaarutyunov/$REPO --json defaultBranchRef \
        --jq .defaultBranchRef.name)
  git -C "$REPO" worktree add "../$REPO-issue-$N" -b "issue-$N" "origin/$DEF"
fi
```

### 4. Create a branch and a PR

If you cloned fresh, branch from the default branch:

```bash
cd <repo>            # or the worktree dir
git checkout -b issue-<N>
git commit --allow-empty -m "Start work on #<N>"
git push -u origin issue-<N>
gh pr create --repo gaarutyunov/<repo> --fill \
  --title "<task title>" --body "Closes #<N>"
```

(An empty starter commit lets you open the PR early; squash/amend later.)

### 5. Triage the task

Decide **spec-first** vs **implement-directly**:

- **Needs a spec (openspec)** when the work is *serious*: changing
  architecture, adding/altering public APIs, new functionality, or anything
  spanning multiple projects. Use [OpenSpec](https://github.com/Fission-AI/openspec)
  — it's initialized in this workspace repo (the `/opsx:*` commands and
  `openspec/` config are already present).
- **Implement directly** when it's a contained change: a bug fix, a small
  feature, docs, config, a self-evident tweak.

When unsure, lean toward a spec for anything a reviewer would want to agree on
*before* code is written. If the shape is still fuzzy, run `/opsx:explore` first
to think it through before proposing.

### 6a. Spec-first path (OpenSpec `/opsx:*`)

Specs are authored in **this workspace repo** with OpenSpec, then reviewed and
merged by the owner *before* implementation. OpenSpec's `/opsx:*` commands run in
the AI chat (not the terminal) and write to `openspec/changes/<change>/`.

1. Create the change and its planning artifacts (proposal, specs, design,
   tasks) in one step:

   ```text
   /opsx:propose <repo>-issue-<N>-<slug>
   ```

   (Use `/opsx:update` to revise artifacts, and `/opsx:explore` beforehand if
   you need to think first. Kebab-case the change name.)

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

Then **wait for the owner to approve and merge** the spec PR (apply the review &
merge discipline in step 10). Do not start implementation until it is merged.
When looping, this is a hard gate — leave the task in **In progress** and move
on / pause (see Looping).

Once the spec PR is merged, implement from the change's `tasks.md` with
`/opsx:apply`, and after the work ships, finalize the change with
`/opsx:archive` (moves it to `openspec/changes/archive/`).

### 6b. Direct-implementation path

Skip straight to the work in the code repo's branch/PR from step 4.

### 7. Perform the work

Implement in the code repo's branch/worktree, keeping changes scoped to the
task and adding/adjusting tests where the project has them.

- **Spec-first tasks:** drive the implementation from the merged change's
  `tasks.md` with `/opsx:apply`, then `/opsx:archive` the change once the work
  has shipped.
- **Direct tasks:** implement against the issue.

### 8. Commit, push

Stage only the paths you intended to change — never `git add -A`, which can
sweep in unrelated local edits, generated files, or accidentally-present
secrets. Review the staged diff before committing:

```bash
git add <path> [<path> ...]     # the specific files for this task
git diff --cached               # inspect exactly what will be committed
git commit -m "<clear message>" # ref the issue/spec
git push
```

Ensure the PR is up to date and its body links the issue (`Closes #<N>`) and,
if applicable, the merged spec PR.

### 9. Move the task to **In review**

```bash
gh project item-edit --project-id <PROJECT_ID> --id <ITEM_ID> \
  --field-id <STATUS_FIELD_ID> --single-select-option-id <IN_REVIEW_OPTION_ID>
```

Report: task title, code PR URL, spec PR URL (if any), and what was done.

### 10. Review & merge discipline

**Never merge a PR/MR with unresolved review threads.** Before merging any PR
(a code PR, or a spec PR once the owner has approved it), work the threads in
this order:

1. **Owner (human) comments first.** Address every review comment written by the
   repo owner. These take priority over any bot.
2. **Then CodeRabbit comments you find valid.** CodeRabbit posts findings with a
   `🤖 Prompt for AI Agents` block containing the exact fix. Pull them all with
   the bundled helper:

   ```bash
   .claude/skills/hitl-loop/scripts/coderabbit-prompts.py gaarutyunov/<repo> <PR#>
   ```

   **Verify each finding against the current code** — CodeRabbit is often right
   but not always. Fix the still-valid ones (keep changes minimal); for any you
   judge invalid, skip the code change but still reply with a brief reason.

   > **If CodeRabbit's review limit is reached, ignore it.** When CodeRabbit
   > posts a "review limit reached" / "rate limited" notice instead of an actual
   > review (its status check can still show green — that's just the notice), do
   > **not** block on it: there are no bot threads to work, so treat this step as
   > satisfied and proceed to the merge on the strength of the owner's review
   > alone. Don't wait for or re-trigger the bot. (You *may* leave a
   > `@coderabbitai review` comment for later, but never gate the merge on it.)
3. **Resolve every thread.** After fixing, reply to the thread (reference the
   fixing commit) and resolve it; for a declined finding, reply with the reason
   and resolve. A thread is resolved via the GraphQL `resolveReviewThread`
   mutation (there is no REST endpoint):

   ```bash
   # find thread ids + resolved state:
   gh api graphql -f query='query { repository(owner:"gaarutyunov", name:"<repo>") {
     pullRequest(number: <PR#>) { reviewThreads(first:50) {
       nodes { id isResolved comments(first:1){ nodes { author{login} body } } } } } }'
   # resolve one:
   gh api graphql -f query='mutation { resolveReviewThread(input:{threadId:"<PRRT_...>"}) { thread { isResolved } } }'
   ```

4. **Only then merge**, once all threads are resolved and checks are green:

   ```bash
   gh pr merge <PR#> --repo gaarutyunov/<repo> --squash
   ```

For a **spec PR**, the owner still merges it (step 6a) — but the same rule
applies: no unresolved threads before that merge.

## Looping

To process the board continuously, drive this skill with the `/loop` skill
(e.g. `/loop /hitl-loop` for self-paced, or `/loop 15m …`). Each
iteration handles one task end-to-end:

- If there is no **Ready** task marked **Loop = hitl**, do nothing and wait for
  the next tick. (`auto`-marked and unrouted tasks are not this loop's.)
- If a task is blocked on **spec approval** (step 6a), leave it in
  **In progress**, note that it's awaiting review, and pick up the next Ready
  task (or idle if none) rather than blocking the whole loop.
- Never move a task to **In review** until its work is pushed.

## Related skills

- `pet-project-metadata` — ensure a new/updated repo has the required metadata.
- `subdomain-setup` — publish the result at `<name>.garutyunov.com`.
- `ui-kit` — build the UI with the shared design system.
- `icon-generation` — generate the project/app icon.
