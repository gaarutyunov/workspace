## 1. GitHub discovery module

- [ ] 1.1 Add `lib/github-projects.ts` exporting `discoverPetProjects(): Promise<Project[]>`.
- [ ] 1.2 Fetch `GET /search/repositories?q=topic:pet-project+user:gaarutyunov` with Node `fetch`; send `Authorization: Bearer $GITHUB_TOKEN` when the env var is present, unauthenticated otherwise; set an explicit `user-agent` and the GitHub API `Accept` header.
- [ ] 1.3 Map each repo to `Project`: `id=repo.name`, `url=repo.homepage`, `fallback={ name: repo.name, description: repo.description ?? "", created: repo.created_at.slice(0,10), icon: <placeholder> }`.
- [ ] 1.4 Filter: drop repos with empty `homepage`, drop `fork`/`archived`, drop the `garutyunov.com` repo, keep public only.
- [ ] 1.5 Sort by `created` descending for deterministic order.
- [ ] 1.6 Wrap the whole thing in try/catch: on any error/non-OK/timeout return `[]` and `console.warn` a build-time notice. (Never throw.)

## 2. Wire into the page

- [ ] 2.1 In `app/page.tsx`, replace the static `projects` import with `const projects = await discoverPetProjects();` before `fetchAllProjectMeta(projects)`.
- [ ] 2.2 Confirm `lib/og.ts` is unchanged and still consumes `Project[]` (empty list renders an empty section without error).

## 3. Retire the static list and dead assets

- [ ] 3.1 Remove the exported `projects` array from `lib/projects.ts`; keep the `Project` / `ResolvedMeta` / `ResolvedProject` types.
- [ ] 3.2 Add a bundled placeholder icon (for the rare no-`og:image` case) and reference it as the fallback icon.
- [ ] 3.3 Remove the now-unused `public/projects/*.png` icons (cleanup).

## 4. Verify

- [ ] 4.1 `npm run lint` and typecheck (`tsc --noEmit` / the project's typecheck script) pass.
- [ ] 4.2 `npm run build` succeeds and the pet-projects section renders the discovered repos (verify boids + stereoscope appear, ordered newest-first, with icons from their live `og:image`).
- [ ] 4.3 Simulate GitHub failure (e.g. bad token / offline) and confirm `npm run build` still completes with an empty section and a warning.
- [ ] 4.4 Ensure the CI build workflow has `GITHUB_TOKEN` available (Actions provides it by default); document the env var if a custom token is used.
