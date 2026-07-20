## Context

garutyunov.com is a Next.js static-export site. `app/page.tsx` (a Server
Component) calls `fetchAllProjectMeta(projects)` from `lib/og.ts` at build time;
`og.ts` fetches each project's live URL with Node `fetch`, parses OG/HTML meta,
and bakes `ResolvedProject[]` into the static page, falling back to per-project
`fallback` values when the live site is unreachable. Today `projects` is a
hand-maintained array in `lib/projects.ts` — the only reason a code change is
needed to add a project.

Each pet project already self-describes on GitHub: the `pet-project` topic
(added by the `pet-project-metadata` conventions) and a `homepage` set to its
GitHub Pages URL. So the static array can be replaced by a build-time GitHub
query with no change to the downstream crawl/render.

## Goals / Non-Goals

**Goals:**
- Discover the project list from GitHub at build time (topic `pet-project`,
  owner `gaarutyunov`).
- Reuse `lib/og.ts` unchanged — only swap the data source in front of it.
- Never break `next build` when GitHub is unavailable.
- Keep the rendered output identical in shape to today's.

**Non-Goals:**
- Runtime/client-side fetching — discovery stays at build time (static export).
- Changing the crawl/parse logic or the card UI.
- A general multi-owner or org-wide crawler — scoped to `gaarutyunov`.
- Incremental/ISR revalidation — a rebuild refreshes the list (matches current
  static-export model).

## Decisions

### D1: REST search `GET /search/repositories?q=topic:pet-project user:gaarutyunov`
One request returns all tagged repos with the fields needed (`name`, `homepage`,
`description`, `created_at`, `fork`, `archived`). Simpler than listing all repos
and filtering topics client-side, and the result set is tiny.
- *Alternative — `GET /users/gaarutyunov/repos` + filter `topics`:* needs the
  `topics` preview media type per repo or a second call each; more requests.
  Rejected.
- *Alternative — GraphQL:* one typed query, but adds a client/schema for a tiny
  win. Rejected for a plain `fetch` to the REST endpoint (consistent with
  `og.ts`, which uses bare `fetch`).

### D2: Build-time auth via `GITHUB_TOKEN`, unauthenticated fallback
Read `process.env.GITHUB_TOKEN` (GitHub Actions injects it automatically) and
send `Authorization: Bearer` when present (5000 req/hr). When absent, attempt the
request unauthenticated (60 req/hr — still fine for one search call locally).
Never hard-require the token.

### D3: Map repo → `Project`, homepage → url, GitHub fields → fallback
`{ id: repo.name, url: repo.homepage, fallback: { name: repo.name,
description: repo.description ?? "", created: repo.created_at.slice(0,10),
icon: <placeholder> } }`. Icon has no GitHub source, so the fallback icon is a
neutral placeholder (e.g. a bundled default) and the *real* icon comes from the
live page's `og:image` through the existing crawl. Since every pet project ships
`og:image` per the metadata conventions, the placeholder is rarely shown.
- Skip repos with empty `homepage`, and skip `fork`/`archived` repos.

### D4: Exclude the site repo and order deterministically
Filter out `garutyunov.com` by name. Sort by `created` descending (newest first)
for a stable, meaningful order independent of GitHub's API ordering.

### D5: Graceful degradation — discovery returns `[]` on failure
`discoverPetProjects()` wraps the fetch in try/catch and returns `[]` (or a small
committed fallback list) on any error/non-OK/timeout, so `next build` always
succeeds. `og.ts` already tolerates an empty list. Log a build warning so a
silent-empty homepage is noticeable in CI logs.
- *Trade-off:* an empty list on a transient GitHub outage means a build shipped
  during the outage shows no projects. Acceptable given rebuilds are cheap and
  the outage window is small; a committed minimal fallback list can be added if
  this proves annoying.

### D6: `lib/projects.ts` keeps the types, loses the data
The `Project` / `ResolvedMeta` / `ResolvedProject` interfaces remain (the
pipeline contract). The exported `projects` array is removed; `app/page.tsx`
calls `discoverPetProjects()` then `fetchAllProjectMeta(...)`. The committed
`public/projects/*.png` icons become dead assets — remove them as cleanup (icons
now come from `og:image`).

## Risks / Trade-offs

- **[GitHub outage/rate-limit at build → empty projects section]** → try/catch
  returns `[]` and logs a warning; rebuild recovers. Optional committed fallback
  list if needed.
- **[A pet project without `og:image` shows a placeholder icon]** → covered by
  the `pet-project-metadata` conventions (every project ships OG tags); the
  placeholder is the safety net, not the norm.
- **[A repo tagged `pet-project` but not meant to be public/listed]** → the topic
  is the opt-in; anything tagged is intended to be listed. Fork/archived filter
  removes obvious noise.
- **[Description drift between GitHub and the live og:description]** → live
  `og:description` wins (existing pipeline precedence), so the site reflects the
  page, not stale repo text.
- **[Unauthenticated local builds hit the 60/hr limit]** → one search call per
  build; negligible. Token recommended in CI, not required.

## Migration Plan

- Additive then subtractive: introduce `discoverPetProjects()`, switch
  `app/page.tsx` to it, then delete the static `projects` array and (optionally)
  the `public/projects/*.png` icons in the same PR.
- Rollback: restore the static `projects` array export and point `app/page.tsx`
  back at it — the crawl pipeline is untouched, so rollback is a one-file revert.

## Open Questions

- Whether to keep a tiny committed fallback list (e.g. stereoscope) for the
  outage case, or accept an empty section. Leaning toward empty + warning for
  simplicity; revisit if outages bite.
- Exact placeholder icon for the rare no-`og:image` case (a generic project glyph
  vs the site favicon). To be decided in implementation.
- Whether to also filter by `visibility: public` explicitly (search already only
  returns public repos for an unauthenticated query; with a token it could
  surface privates — add an explicit public filter to be safe).
