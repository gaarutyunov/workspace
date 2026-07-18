# workspace

Workspace for agentic development.

Pet-project code repos are cloned into `projects/` (gitignored). Reusable agent
skills for managing pet projects and [garutyunov.com](https://github.com/gaarutyunov/garutyunov.com)
live in `.claude/skills/`.

## Skills

Authored in this repo:

| Skill | What it does |
| --- | --- |
| [`ui-kit`](.claude/skills/ui-kit/SKILL.md) | Use the [GA UI Kit](https://github.com/gaarutyunov/ui-kit) (`@gaarutyunov/ui-kit`) web components on pet projects and the personal site. |
| [`pet-project-metadata`](.claude/skills/pet-project-metadata/SKILL.md) | Apply/audit the standard metadata every pet project needs (description, `pet-project` topic, homepage subdomain, `SPEC.md`, `README.md`, Pages config). |
| [`subdomain-setup`](.claude/skills/subdomain-setup/SKILL.md) | Publish a repo at `<name>.garutyunov.com` — Cloudflare DNS + GitHub Pages custom domain, HTTPS enforcement, and set Pages as the repo website. |
| [`hitl-loop`](.claude/skills/hitl-loop/SKILL.md) | **Human-in-the-loop** board driver. Work the [project board](https://github.com/users/gaarutyunov/projects/6): pull a Ready task → In progress → clone/worktree → branch + PR → triage (openspec vs direct) → spec approval gate → work → In review. Includes review/merge discipline (address owner then valid CodeRabbit comments; never merge with unresolved threads) and a `coderabbit-prompts.py` helper. Loopable with `/loop`. |
| [`auto-loop`](.claude/skills/auto-loop/SKILL.md) | **Autonomous** variant of `hitl-loop`: same flow but no human gates — doesn't wait for spec approval or code review, self-merges each PR once CI is green, then moves the task to Done. For unattended runs where CI is the trust boundary. Loopable with `/loop`. |
| [`icon-generation`](.claude/skills/icon-generation/SKILL.md) | Generate the standard minimalist 3D voxel app icon via OpenRouter's image models. |

Installed via [`npx skills`](https://skills.sh) (tracked in `skills-lock.json`):

| Skill | Source | What it does |
| --- | --- | --- |
| `find-skills` | `vercel-labs/skills` | Discover and install more agent skills on demand. |
| `vercel-react-best-practices` | `vercel-labs/agent-skills` | React 19 / Next.js App Router performance & data-fetching best practices — matches the site + pet-project frontend stack. |
| `golang-pro` | `jeffallan/claude-skills` | Idiomatic Go: concurrency, generics, gRPC/REST services, testing, performance. |
| `kubernetes-specialist` | `jeffallan/claude-skills` | Kubernetes workloads, Helm, RBAC, networking, GitOps, troubleshooting. |

Installed via [OpenSpec](https://github.com/Fission-AI/openspec) (`openspec init`): the
`openspec-*` skills and `/opsx:*` commands (`.claude/commands/opsx/`) that drive the
spec-driven `propose → apply → archive` workflow; project config in `openspec/`.

Invoke a skill with `/<name>` (e.g. `/hitl-loop`), or let Claude Code
auto-select it from the task description. Restore the `npx skills` set on a fresh
checkout with `npx skills experimental_install`.
