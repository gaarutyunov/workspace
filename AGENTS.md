# Project instructions

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`, never `CLAUDE.md`.

## Skills

Install skills into this repo, never globally.

- Run `npx skills add <source> --skill <name>` from the repo root (project-level is the default). Do NOT pass `-g` / `--global`.
- Source of truth lives in `.agents/skills/<name>/`; `.claude/skills/<name>` is a symlink to `../../.agents/skills/<name>`.
- `skills-lock.json` tracks installed skills.
- If a skill installs as a real directory under `.claude/skills/`, migrate it: move it to `.agents/skills/<name>/` and replace the original with a symlink.
