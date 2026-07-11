# Project instructions

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`, never `CLAUDE.md`.

## Git

Never push to `main`. Always create a feature branch, push it, and open a pull request — even for small changes. Let the PR be reviewed/merged rather than pushing directly.

## Skills

Install skills into this repo, never globally.

- Run `npx skills add <source> --skill <name> --agent claude-code` from the repo root (project-level is the default). Do NOT pass `-g` / `--global`.
- ALWAYS pass `--agent claude-code`. Without it the CLI fans out to ~26 other agent dirs (`.cursor`, `.codex`, `.roo`, `.windsurf`, …); those are gitignored and must never be committed.
- Source of truth lives in `.agents/skills/<name>/`; `.claude/skills/<name>` is a symlink to `../../.agents/skills/<name>`.
- `skills-lock.json` tracks installed skills.
- If a skill installs as a real directory under `.claude/skills/`, migrate it: move it to `.agents/skills/<name>/` and replace the original with a symlink.
