## 1. GitHub discovery module

- [ ] 1.1 Add `lib/github-projects.ts` exporting `discoverPetProjects(): Promise<Project[]>`.
- [ ] 1.2 Read `process.env.GITHUB_TOKEN` — **required**. If absent, throw with a clear message (no unauthenticated fallback). Fetch `GET /search/repositories?q=topic:pet-project+user:gaarutyunov` with Node `fetch`, sending `Authorization: Bearer $GITHUB_TOKEN`, an explicit `user-agent`, and the GitHub API `Accept` header.
- [ ] 1.3 Map each repo to `Project`: `id=repo.name`, `url=repo.homepage`, `fallback={ name: repo.name, description: repo.description ?? "", created: repo.created_at.slice(0,10) }`. **No placeholder icon** — the card image comes from the live page's `og:image` (guaranteed by the social-image skill, workspace#12).
- [ ] 1.4 Filter: drop repos with empty `homepage`, drop `fork`/`archived`, drop the `garutyunov.com` repo. **Do not filter by visibility** — private repos with a public website are included (D7).
- [ ] 1.5 Sort by `created` descending for deterministic order.
- [ ] 1.6 On any error/non-OK/timeout/missing-token, **throw** so `next build` fails loudly. No try/catch that returns `[]`, no last-known/committed fallback list.

## 2. Wire into the page

- [ ] 2.1 In `app/page.tsx`, replace the static `projects` import with `const projects = await discoverPetProjects();` before `fetchAllProjectMeta(projects)`.
- [ ] 2.2 Confirm `lib/og.ts` is unchanged and still consumes `Project[]`.

## 3. Retire the static list and dead assets

- [ ] 3.1 Remove the exported `projects` array from `lib/projects.ts`; keep the `Project` / `ResolvedMeta` / `ResolvedProject` types.
- [ ] 3.2 Remove the now-unused `public/projects/*.png` icons (cleanup) — images come from `og:image`; no placeholder asset is added.

## 4. Verify

- [ ] 4.1 `npm run lint` and typecheck (`tsc --noEmit` / the project's typecheck script) pass.
- [ ] 4.2 With `GITHUB_TOKEN` set, `npm run build` succeeds and the pet-projects section renders the discovered repos (verify boids + stereoscope appear, ordered newest-first, with images from their live `og:image`).
- [ ] 4.3 Confirm the no-fallback behavior: with a bad/absent token or GitHub unreachable, `npm run build` **fails loudly** with a clear error (it does not ship an empty section).
- [ ] 4.4 Confirm a **private** repo with the topic + a published homepage is listed, sourced only from public metadata + its published site (no source access).
- [ ] 4.5 Ensure the CI build workflow provides `GITHUB_TOKEN` (Actions injects it by default; document if a custom token/scope is needed to see private repos).
