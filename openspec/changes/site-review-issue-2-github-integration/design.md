## Context

Site Review is a pnpm monorepo:

- `packages/shared` — types + slug generation.
- `packages/server` — Express REST API (`/ingest`, `/comments`, `/pages`, `/slugs`)
  plus a stateless MCP Streamable-HTTP endpoint, backed by a single on-disk SQLite
  store (`better-sqlite3`). Runs on `localhost:4711` (also shippable as a container).
- `packages/extension` — WXT + React MV3 extension; a background service worker owns
  IndexedDB and mirrors comments to the server.
- `packages/landing` — buildless landing page; its PR previews deploy under
  `…/pr-preview/pr-<N>/` (the `rossjrw/pr-preview-action` convention). This is the
  exact path shape the issue references.

The server is a long-lived local process that already owns durable state, so it is
the natural place to hold GitHub credentials and perform GitHub API calls. The
extension stays a thin client that calls new server endpoints.

## Goals / Non-Goals

**Goals:**
- Authenticate the user to GitHub via a GitHub App (OAuth user-to-server), server-side.
- Bind a reviewed page's origin to a repository and remember it.
- Auto-propose the repo (from page HTML) and the PR (from the URL path).
- Sync a page's open comments to a PR, or to an appended/new issue when there is no PR.
- Make re-syncs idempotent (no duplicate GitHub content).

**Non-Goals:**
- Two-way sync (pulling GitHub comment edits/resolutions back into Site Review).
- Line-anchored PR *diff* review comments tied to specific files/hunks — Site Review
  comments anchor to DOM elements, not source lines, so they map to PR-level review
  comments, not inline code comments.
- Supporting GitHub Enterprise / non-github.com hosts in this change.
- A hosted multi-tenant OAuth backend — this targets the single-user local server.

## Decisions

### D1: GitHub App + OAuth device flow (not a web-callback OAuth App)
The server is a local process without a stable public callback URL, so the OAuth
**device authorization flow** fits best: the server requests a device/user code, the
extension shows the user the code + `github.com/login/device` URL, the server polls
for the token. This avoids running a public redirect endpoint and works identically
for the container deployment.
- *Alternative — web application flow with `http://localhost:4711/github/callback`:*
  workable for the local case but breaks for the container/remote case and needs the
  browser redirected back to a server route. Rejected as the default; the design keeps
  the token-exchange step behind an interface so a callback flow can be added later.
- A **GitHub App** (vs a plain OAuth App) is required by the issue ("as an App") and
  gives per-repo installation scoping and finer permissions (issues/PRs read+write).

### D2: Octokit as the GitHub client
Use `@octokit/*` (REST + auth-oauth-device) rather than hand-rolling fetch calls —
it handles pagination, auth token refresh, and rate-limit headers. Single new runtime
dependency in `packages/server`.

### D3: Tokens and bindings live in SQLite, alongside comments
Add tables to the existing `better-sqlite3` DB:
- `github_auth(id INTEGER PK CHECK(id=1), login, access_token, token_expires_at,
  refresh_token, created_at, updated_at)` — a single-row table (one connected user
  for the local server).
- `github_repo_binding(origin TEXT PK, owner, repo, default_branch, updated_at)` —
  page-origin → repository.
- `github_sync_ledger(comment_id, target_kind, target_ref, gh_url, synced_at,
  PRIMARY KEY(comment_id, target_kind, target_ref))` — records what was already
  posted so re-syncs are idempotent (D5).
Tokens are write-only from the client's perspective: no endpoint returns
`access_token`/`refresh_token`, and they are never logged (satisfies the
token-confidentiality requirement).

### D4: Target resolution is a pure function over (binding, pageUrl, page HTML)
- **Repo detection:** scan page HTML for `github.com/<owner>/<repo>` links via a
  regex, drop non-repo paths (`/features`, `/login`, gists, `sponsors`, etc.),
  dedupe, rank (prefer a repo whose owner matches the connected account / appears in
  a canonical link/meta tag). Return candidates; the extension already has the DOM,
  so it can also pass extracted candidates to the server to avoid re-fetching.
- **PR detection:** parse the URL path with `/pr-preview/pr-(\d+)\//`. A hit is
  *verified* against the GitHub API (open PR exists) before being used; on miss, fall
  back to issue mode.
- Output is a single `SyncTarget` descriptor: `{ kind: 'pr'|'issue-existing'|'issue-new',
  ... }` consumed by the sync step.

### D5: Idempotent sync via the ledger, comment content addressed by id
Each open comment for the page is checked against `github_sync_ledger` for the
resolved target; only unsynced comments are posted. For PRs the sync creates a PR
**review** (or individual review comments) — for issues it appends a comment or
creates a new issue. Every created artifact's URL + the comment ids it covered are
written to the ledger. Re-running posts only the delta. Each posted body embeds the
element slug + page URL so the GitHub reader knows what was commented on.

### D6: New server endpoints (REST, extension-facing)
- `POST /github/connect` → start device flow, returns `{ userCode, verificationUri, expiresIn }`.
- `GET  /github/status` → `{ authenticated, login? }` (polls also advance the device flow).
- `POST /github/disconnect`.
- `GET  /github/repos` → accessible repositories.
- `POST /github/bind` `{ origin, owner, repo }` / `GET /github/binding?origin=` / `DELETE /github/binding`.
- `POST /github/detect` `{ pageUrl, htmlCandidates? }` → `{ repoCandidates, detectedPr }`.
- `GET  /github/issues?owner=&repo=` → open issues for the picker.
- `POST /github/sync` `{ pageUrl, target }` → `{ synced, skipped, links[] }`.

### D7: Config via environment, documented in README
`GITHUB_APP_CLIENT_ID` (and, if the chosen flow needs it, `GITHUB_APP_ID` /
`GITHUB_APP_PRIVATE_KEY`) are read from env; nothing committed. README gains a
"Connect to GitHub" section describing the one-time GitHub App creation and the env
vars. Absence of config makes `/github/*` return a clear "not configured" error
rather than crashing.

## Risks / Trade-offs

- **[Element comments don't map to code lines]** → Sync to PR-level review comments /
  issue bodies with slug + URL context, not inline diff comments. Documented as a
  Non-Goal; revisit if a source mapping ever exists.
- **[Repo auto-detection false positives]** (a page linking many repos) → Never
  auto-bind silently; always surface candidates and require the user to confirm the
  connection.
- **[Token storage in plaintext SQLite]** → Acceptable for a single-user local tool
  (same trust boundary as the DB itself); mitigated by never returning/logging tokens
  and supporting disconnect. A future encryption-at-rest pass is out of scope here.
- **[Device-flow polling latency / expiry]** → Surface `expiresIn`, let the user
  restart; poll on `/github/status` calls the extension already makes.
- **[GitHub rate limits]** → Octokit surfaces limit headers; sync batches per page and
  the ledger prevents redundant calls on re-sync.
- **[Duplicate content if the ledger and GitHub diverge]** (comment posted but ledger
  write fails) → Write the ledger row in the same logical step as recording the
  created URL; on partial failure a re-sync may re-post, an acceptable degradation for
  v1.

## Migration Plan

- Purely additive: new tables are created with `CREATE TABLE IF NOT EXISTS` on
  startup (matching the existing store bootstrap); no migration of existing rows.
- Rollback: the feature is inert without `GITHUB_APP_*` env vars; unsetting them
  disables `/github/*`. Dropping the new tables leaves comment functionality intact.

## Open Questions

- Exact GitHub App permission set — minimally `issues: read/write`,
  `pull_requests: read/write`, `metadata: read`, `contents: read` (for repo listing).
  To be finalized when the app is registered.
- PR sync granularity: a single PR **review** summarizing all comments vs one review
  comment per Site Review comment. Leaning toward one review with a body listing each
  comment (simpler, fewer API calls); confirm during implementation.
- Whether to reuse the extension-supplied HTML candidates or have the server fetch the
  page itself for detection (the extension already has the live DOM, so passing
  candidates is preferred and avoids auth-walled fetches).
