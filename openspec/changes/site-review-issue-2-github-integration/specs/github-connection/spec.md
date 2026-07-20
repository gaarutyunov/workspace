## ADDED Requirements

### Requirement: GitHub App OAuth authentication

The server SHALL let a user authenticate to GitHub through a GitHub App using an
OAuth user-authorization flow, and SHALL persist the resulting user access token
server-side. The flow MUST NOT require the user to paste a personal access token.

#### Scenario: User starts the connect flow
- **WHEN** the user triggers "Connect GitHub" from the extension
- **THEN** the server begins a GitHub App OAuth flow and returns to the extension
  the information needed to complete it (an authorization URL to open, or a device
  user-code and verification URL)

#### Scenario: Authorization completes successfully
- **WHEN** the user authorizes the app in GitHub and the flow completes
- **THEN** the server exchanges the grant for a user access token, stores it, and
  reports the connection as authenticated together with the authenticated GitHub
  login

#### Scenario: Authorization is denied or times out
- **WHEN** the user denies authorization or the flow expires before completion
- **THEN** the server does not store any token and reports the connection as not
  authenticated with a reason

### Requirement: Connection status and disconnect

The server SHALL expose the current GitHub connection status and SHALL let the
user disconnect, discarding any stored token.

#### Scenario: Query status while connected
- **WHEN** the extension requests the GitHub connection status and a valid token
  is stored
- **THEN** the server reports authenticated together with the GitHub login

#### Scenario: Disconnect
- **WHEN** the user disconnects GitHub
- **THEN** the server deletes the stored token and subsequent status requests
  report not authenticated

### Requirement: List accessible repositories

While authenticated, the server SHALL list the repositories the user can access
through the app installation, so the user can choose one to connect.

#### Scenario: List repos when authenticated
- **WHEN** the extension requests accessible repositories and the user is
  authenticated
- **THEN** the server returns the repositories reachable via the app
  (owner/name and default branch), paginated if necessary

#### Scenario: List repos when not authenticated
- **WHEN** the extension requests accessible repositories and no valid token is
  stored
- **THEN** the server responds with an unauthenticated error and returns no
  repositories

### Requirement: Bind a reviewed page origin to a repository

The server SHALL persist a binding from a reviewed page's origin to a chosen
GitHub repository, and SHALL return that binding on subsequent visits so the
connection persists across sessions.

#### Scenario: Connect a repository to the current page
- **WHEN** the user selects a repository to connect for a page
- **THEN** the server stores a binding keyed by the page origin and reports the
  page as connected to that repository

#### Scenario: Binding is remembered on return
- **WHEN** the user revisits a page whose origin was previously bound
- **THEN** the server reports the same connected repository without requiring the
  user to choose again

#### Scenario: Change or remove the binding
- **WHEN** the user connects a different repository for an origin, or clears it
- **THEN** the server replaces or removes the stored binding accordingly

### Requirement: Token confidentiality

Stored GitHub tokens MUST NOT be returned by any read/query endpoint and MUST NOT
appear in logs or in comment payloads.

#### Scenario: Token never leaves the server
- **WHEN** any status, repo-list, detection, or sync response is produced
- **THEN** the response contains no access token or client secret material
