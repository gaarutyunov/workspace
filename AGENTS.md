# Project instructions

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`, never `CLAUDE.md`.

## Git

Never push to `main`. Always create a feature branch, push it, and open a pull request — even for small changes. Let the PR be reviewed/merged rather than pushing directly.

**Always branch from fresh upstream default.** Before creating a branch in any repo, `git fetch origin` and branch off `origin/<default>` (resolve the real default branch — don't assume `main`), never off a possibly-stale local checkout. Branching from a stale main produces a branch that's behind and conflict-prone.

## Board work: interact through GitHub, never in the chat

When working the project board (the `hitl-loop` / `auto-loop` / `loop-common` skills), **all owner interaction happens on GitHub**. Never use `AskUserQuestion` and never ask a question in the Claude Code window — a tick may run unattended, so a question asked there is a question nobody sees. Post it on the issue instead (with your recommended option), label it `needs:input`, and move the item to **In review**.

Corollaries, all detailed in `.claude/skills/loop-common/SKILL.md`:

- Every tick starts with `.claude/skills/loop-common/scripts/board-tick.py` — never hand-roll board or comment queries.
- The board has exactly six statuses (Backlog, Ready, In progress, In review, Blocked, Done). Every other intermediate state is a **label**, and adding a seventh status needs its own issue, as `Blocked` got. The owner sets only `approved:spec` / `approved:pr` and only ever moves an item to **Ready**; every other status move is the agent's.
- **Blocked** means "waiting on another issue"; **In review** means "waiting on a human", for any reason — review, spec approval, an answer, a credential, a product decision. Nothing waiting on either is ever left **In progress**.
- Every comment the agent posts carries the agent marker (use `board-tick.py post`), and every owner comment acted on is acked (`board-tick.py ack`) so it never re-surfaces.

## Cloning repos

Clone any external repo (pet projects, repos you're inspecting) into `projects/`, never the workspace root. `projects/.gitignore` is `*` (with `!.gitignore`), so everything under it is ignored and can never be accidentally committed into this repo. Clone each repo **once**; keep its base checkout on the default branch and give every task its own git worktree under `projects/<repo>/.worktrees/<branch>` (add `.worktrees/` to the repo's `.git/info/exclude` so it stays out of that repo's git status). Create the worktree from fresh `origin/<default>` per the branch rule above.

After a repo lands under `projects/`, register it with the machine-wide gortex daemon so the graph/MCP code tools can query it: `gortex track projects/<repo>` for the base clone, and `gortex track --as-worktree projects/<repo>/.worktrees/<branch>` for **each worktree** — gortex does **not** auto-index worktrees (a worktree is untracked in the base repo, so a plain `gortex track <repo>` misses it; verified empirically). The graph tools return nothing for a path no tracked repo covers; re-tracking an already-tracked path is a harmless no-op. This workspace itself is registered for the gortex MCP via `.mcp.json` + `.claude/settings.json` (committed) — the latter also carries the gortex agent hooks (SessionStart, PreToolUse, UserPromptSubmit, PreCompact, Stop) so everyone working the workspace gets them; they invoke bare `gortex` (PATH-resolved), so gortex must be installed and on `$PATH`. The workspace repo is **never tracked/indexed** — only the project clones under `projects/` are. A committed `.gortex.yaml` excludes `*` as a guard so that even an accidental `gortex track` of this repo indexes zero source files.

## Skills

Install skills into this repo, never globally.

- Run `npx skills add <source> --skill <name> --agent claude-code` from the repo root (project-level is the default). Do NOT pass `-g` / `--global`.
- ALWAYS pass `--agent claude-code`. Without it the CLI fans out to ~26 other agent dirs (`.cursor`, `.codex`, `.roo`, `.windsurf`, …); those are gitignored and must never be committed.
- Source of truth lives in `.agents/skills/<name>/`; `.claude/skills/<name>` is a symlink to `../../.agents/skills/<name>`.
- `skills-lock.json` tracks installed skills.
- If a skill installs as a real directory under `.claude/skills/`, migrate it: move it to `.agents/skills/<name>/` and replace the original with a symlink.

### Which skill for which work

Skills are only useful if the agent doing the work knows to reach for them.

**Go projects** follow the `go-project-scaffold` skill — the house standard for
scaffolding a Go service *and* for reviewing or refactoring an existing one:
code generation over hand-rolling, OpenTelemetry semantic conventions, cobra,
koanf (never Viper), wire, and the TDD loop with testcontainers. It is derived
from the worked reference in `gaarutyunov/skill-test` PR #2, which is the
tie-breaker when the skill and reality disagree.

Underneath that house standard sit the general-purpose Go skills from
[spf13/go-skills](https://github.com/spf13/go-skills), by the author of Cobra,
Viper and Hugo:

- **`go`** — idiomatic Go: package design, error handling, interfaces,
  concurrency, testing, project layout. Use it for *any* Go work in
  `projects/`, not only new code.
- **`cobra-viper`** — CLI architecture. Take the **Cobra** half as written.
  **Do not use Viper: configuration here is [koanf](https://github.com/knadh/koanf).**
  The skill is left exactly as upstream published it, and the exception —
  with the translation from each Viper call to its koanf equivalent — lives in
  [`.claude/rules/go-cli-koanf.md`](./.claude/rules/go-cli-koanf.md), because an
  edit inside a vendored skill is lost the next time it is reinstalled.
- **`go-spec-reviewer`** — reviews a design doc, spec or RFC for a Go program
  *before* implementation. **Run it on the spec of any Go change** — in this
  repo that means an OpenSpec change under `openspec/changes/` whose target is a
  Go project, before the spec PR is opened for approval. It is the step that
  catches over-engineering while the cost of changing course is still a
  paragraph rather than a branch.

The Go rules in `.claude/rules/` are path-scoped and apply on top of all of
these: `go-test-assertions.md` (testify, not hand-rolled comparisons),
`go-test-mocks.md` (generated gomock, never hand-rolled doubles), and
`go-cli-koanf.md` (Cobra yes, Viper no).
