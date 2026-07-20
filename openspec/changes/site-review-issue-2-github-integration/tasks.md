## 1. Shared types

- [ ] 1.1 Add GitHub types to `packages/shared`: `GithubConnectionStatus`, `GithubRepo`, `RepoBinding`, `RepoCandidate`, `DetectedPr`, `SyncTarget` (`kind: 'pr' | 'issue-existing' | 'issue-new'`), and `SyncResult` (`synced`, `skipped`, `links`).
- [ ] 1.2 Add a unit test for any pure helper that ends up in shared (e.g. PR-path parsing if placed here).

## 2. Server: persistence

- [ ] 2.1 Extend `CommentStore` (or a new `GithubStore`) with `CREATE TABLE IF NOT EXISTS` for `github_auth` (single-row), `github_repo_binding`, and `github_sync_ledger` per design D3.
- [ ] 2.2 Add store methods: get/set/clear auth; get/set/delete binding by origin; read/record ledger entries by (comment_id, target).
- [ ] 2.3 Ensure tokens are never selected into any list/read path used by HTTP responses; add a store test proving auth rows are isolated.

## 3. Server: GitHub client + OAuth device flow

- [ ] 3.1 Add the Octokit dependency to `packages/server` and a `github/config.ts` reading `GITHUB_APP_CLIENT_ID` (+ `GITHUB_APP_ID`/`GITHUB_APP_PRIVATE_KEY` if needed); return a clear "not configured" state when unset.
- [ ] 3.2 Implement the OAuth **device flow**: start (request device+user code), and token exchange/poll; persist the token via the store on success.
- [ ] 3.3 Implement authenticated client construction from the stored token, with disconnect clearing it.

## 4. Server: detection logic (pure, tested)

- [ ] 4.1 Implement repo detection: extract `github.com/<owner>/<repo>` candidates from supplied HTML/links, filter non-repo paths, dedupe, rank; unit-test with fixtures (single, multiple, none).
- [ ] 4.2 Implement PR-path detection: parse `pr-preview/pr-(\d+)/` from a URL; unit-test hit/miss.
- [ ] 4.3 Implement `resolveSyncTarget(binding, pageUrl, candidates)` combining repo + PR detection with GitHub verification of the PR's existence; fall back to issue mode on miss.

## 5. Server: REST endpoints

- [ ] 5.1 `POST /github/connect`, `GET /github/status`, `POST /github/disconnect`.
- [ ] 5.2 `GET /github/repos`, `POST /github/bind`, `GET /github/binding`, `DELETE /github/binding`.
- [ ] 5.3 `POST /github/detect`, `GET /github/issues`.
- [ ] 5.4 `POST /github/sync`: resolve target, compute unsynced comments via the ledger, post to PR/issue, write ledger, return `SyncResult`. Reject when unauthenticated or no binding.
- [ ] 5.5 Endpoint tests: unauthenticated paths return the unauthenticated error and create no content; sync with no open comments reports nothing to sync.

## 6. Server: sync implementations

- [ ] 6.1 PR sync: post a PR review (or review comments) whose body lists each comment with its slug + page URL.
- [ ] 6.2 Existing-issue sync: append a comment built from the page's open comments.
- [ ] 6.3 New-issue sync: create an issue with title/body from the comments.
- [ ] 6.4 Idempotency: only unsynced comments are posted; re-sync of an unchanged page posts nothing; adding one comment then re-syncing posts exactly one. Cover with a test using a faked GitHub client.

## 7. Extension UI

- [ ] 7.1 Add a GitHub panel (connect/disconnect, show login) that drives the device flow via the new endpoints.
- [ ] 7.2 Scan the current page DOM for repo candidates and let the user connect a repo for the origin (showing the auto-detected default).
- [ ] 7.3 Show the resolved target (detected PR, or issue picker with "create new issue"), and a "Sync to GitHub" action that reports the `SyncResult`.

## 8. Docs, config, and verification

- [ ] 8.1 README: "Connect to GitHub" section (GitHub App creation, required permissions, env vars) and update the endpoints list.
- [ ] 8.2 Run `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`; fix failures.
- [ ] 8.3 Manual smoke: connect account, connect a repo on a page, detect a `pr-preview/pr-N/` URL, sync to PR; and on a non-PR page, append to an issue and create a new issue.
