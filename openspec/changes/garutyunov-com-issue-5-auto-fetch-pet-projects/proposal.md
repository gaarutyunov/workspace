## Why

The pet-projects section on garutyunov.com is fed by a hand-maintained array in
`lib/projects.ts`: every new pet project requires a code change to the site to
appear. Each project already declares itself on GitHub (the `pet-project` topic)
and points at its live site (the repo homepage / GitHub Pages URL), so the site
can discover projects automatically instead of being edited by hand.

## What Changes

- Replace the static `projects: Project[]` list with a **build-time fetch** that
  discovers pet projects from GitHub: all repos owned by `gaarutyunov` carrying
  the `pet-project` topic.
- Use each repo's **homepage** field (the "Use your GitHub Pages website" URL) as
  the project URL fed into the existing `lib/og.ts` crawl pipeline. Repos without
  a homepage are skipped.
- Derive each project's baked-in fallback from GitHub repo metadata (name from
  repo name, description from repo description, `created` from `created_at`); the
  card icon continues to come from the live page's `og:image` via the crawl.
- **BREAKING (internal):** the hand-maintained `projects` array and the
  per-project committed `public/projects/*.png` fallback icons are superseded —
  the project list is now sourced entirely from GitHub at build time.
- The build **must never fail** because GitHub is unreachable or rate-limited:
  discovery degrades gracefully (empty or last-known list) rather than breaking
  `next build`.

## Capabilities

### New Capabilities
- `pet-project-discovery`: build-time discovery of pet projects from GitHub by
  the `pet-project` topic, extraction of each project's homepage URL, mapping to
  the pipeline's `Project` shape, filtering/ordering, and graceful degradation
  when the GitHub API is unavailable.

### Modified Capabilities
<!-- No pre-existing OpenSpec specs in this repo; the existing crawl pipeline
     (lib/og.ts) is reused unchanged, so there is no spec-level behavior to
     modify — only a new data source in front of it. -->

## Impact

- **`lib/projects.ts`**: the exported static `projects` array is removed/replaced;
  the `Project` / `ResolvedMeta` / `ResolvedProject` types stay (still the
  pipeline contract).
- **New `lib/github-projects.ts`** (or similar): the GitHub discovery + mapping.
- **`app/page.tsx`**: sources the project list from the new discovery function
  instead of the static array before calling `fetchAllProjectMeta`.
- **`lib/og.ts`**: unchanged — it already consumes `Project[]`.
- **`public/projects/*.png`**: no longer required (icons come from `og:image`);
  removal is optional cleanup.
- **Build/CI**: a `GITHUB_TOKEN` in the Actions build environment for a reliable
  authenticated rate limit; unauthenticated still works within limits.
- Depends on each pet project shipping `og:image` + description on its live page
  and setting its repo homepage — the `pet-project-metadata` conventions.
