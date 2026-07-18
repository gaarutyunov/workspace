# Project instructions

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`, never `CLAUDE.md`.

## Git

Never push to `main`. Always create a feature branch, push it, and open a pull request — even for small changes. Let the PR be reviewed/merged rather than pushing directly.

**Always branch from fresh upstream default.** Before creating a branch in any repo, `git fetch origin` and branch off `origin/<default>` (resolve the real default branch — don't assume `main`), never off a possibly-stale local checkout. Branching from a stale main produces a branch that's behind and conflict-prone.

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
