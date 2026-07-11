# workspace

Workspace for agentic development.

Pet-project code repos are cloned into `projects/` (gitignored). Reusable agent
skills for managing pet projects and [garutyunov.com](https://github.com/gaarutyunov/garutyunov.com)
live in `.claude/skills/`.

## Skills

| Skill | What it does |
| --- | --- |
| [`ui-kit`](.claude/skills/ui-kit/SKILL.md) | Use the [GA UI Kit](https://github.com/gaarutyunov/ui-kit) (`@gaarutyunov/ui-kit`) web components on pet projects and the personal site. |
| [`pet-project-metadata`](.claude/skills/pet-project-metadata/SKILL.md) | Apply/audit the standard metadata every pet project needs (description, `pet-project` topic, homepage subdomain, `SPEC.md`, `README.md`, Pages config). |
| [`subdomain-setup`](.claude/skills/subdomain-setup/SKILL.md) | Publish a repo at `<name>.garutyunov.com` — Cloudflare DNS + GitHub Pages custom domain, HTTPS enforcement, and set Pages as the repo website. |
| [`project-task-loop`](.claude/skills/project-task-loop/SKILL.md) | Work the [project board](https://github.com/users/gaarutyunov/projects/6): pull a Ready task → In progress → clone/worktree → branch + PR → triage (openspec vs direct) → spec approval gate → work → In review. Loopable with `/loop`. |
| [`icon-generation`](.claude/skills/icon-generation/SKILL.md) | Generate the standard minimalist 3D voxel app icon via OpenRouter's image models. |

Invoke a skill with `/<name>` (e.g. `/project-task-loop`), or let Claude Code
auto-select it from the task description.
