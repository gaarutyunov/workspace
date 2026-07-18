# Project instructions

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`, never `CLAUDE.md`.

## Git

Never push to `main`. Always create a feature branch, push it, and open a pull request — even for small changes. Let the PR be reviewed/merged rather than pushing directly.

## Cloning repos

Clone any external repo (pet projects, repos you're inspecting) into `projects/`, never the workspace root. `projects/.gitignore` is `*` (with `!.gitignore`), so everything under it is ignored and can never be accidentally committed into this repo. For a repo that's already cloned there, add a git worktree under `projects/` rather than re-cloning.

## Skills

Install skills into this repo, never globally.

- Run `npx skills add <source> --skill <name>` from the repo root (project-level is the default). Do NOT pass `-g` / `--global`.
- Source of truth lives in `.agents/skills/<name>/`; `.claude/skills/<name>` is a symlink to `../../.agents/skills/<name>`.
- `skills-lock.json` tracks installed skills.
- If a skill installs as a real directory under `.claude/skills/`, migrate it: move it to `.agents/skills/<name>/` and replace the original with a symlink.
