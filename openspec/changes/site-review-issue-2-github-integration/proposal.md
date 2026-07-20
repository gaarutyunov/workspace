## Why

Site Review lets a user annotate any web page with element-anchored comments,
but those comments are trapped in the local server — the only way an agent sees
them is over MCP against `localhost`. When the page being reviewed is a project's
site or a PR preview deploy, the natural home for that feedback is the project's
GitHub repository. Pushing review comments to GitHub (as a PR review or an issue)
turns Site Review from a local-only scratchpad into a way to file actionable,
trackable feedback where the work actually happens.

## What Changes

- Add a **GitHub App + OAuth** connection so the server can act on the user's
  behalf against the GitHub API (authenticate the user, discover their installations
  and accessible repos). Tokens are stored server-side.
- While reviewing a page, let the user **connect a GitHub repository** to that
  page (persisted per page/origin so the choice sticks across visits).
- **Auto-detect the repository** by scanning the reviewed page's HTML for a
  GitHub repo URL and offering it as the default connection.
- **Auto-detect the PR number** from the page URL path — a segment matching
  `pr-preview/pr-<N>/` (the `rossjrw/pr-preview-action` convention this repo's own
  landing page uses) resolves to PR `#<N>` in the connected repo.
- **Sync review comments to GitHub**:
  - When a PR is detected, post the page's open comments to that **PR** (as a PR
    review / review comments).
  - When there is no PR, let the user either **append to an existing issue**
    (picked from the repo's open issues) or **create a new issue** whose body is
    built from the comments.
- Extend the extension UI with a GitHub panel (connect account, choose repo,
  see the detected PR/issue target, trigger a sync) and add the server endpoints
  and persistence it needs.

## Capabilities

### New Capabilities
- `github-connection`: OAuth-based GitHub App authentication and the binding of a
  reviewed page (by origin) to a target GitHub repository, including token
  storage and repo/installation listing.
- `github-target-detection`: deriving the default repo (from page HTML) and the
  PR number (from the URL path) so the sync target is proposed automatically.
- `github-comment-sync`: turning a page's Site Review comments into GitHub
  artifacts — PR review comments when a PR is detected, or an appended/new issue
  otherwise — with idempotent, non-duplicating syncs.

### Modified Capabilities
<!-- No pre-existing OpenSpec specs in this repo; nothing to modify. -->

## Impact

- **packages/server**: new GitHub OAuth + API module, new REST endpoints
  (connect/callback, list repos, detect target, sync), new SQLite tables for
  tokens and page→repo bindings and a sync ledger. New dependency on a GitHub
  API/OAuth client (e.g. Octokit).
- **packages/shared**: new types for GitHub connection state, detected targets,
  and sync results.
- **packages/extension**: new GitHub connection/sync UI in the curtain/settings,
  plus HTML scanning to surface the auto-detected repo.
- **Configuration/secrets**: GitHub App id, client id/secret, and app private
  key supplied via environment; no secrets committed. Requires documenting the
  GitHub App setup in the README.
- **Security**: the server now holds user GitHub tokens — scope, storage, and
  redaction need to be handled deliberately.
