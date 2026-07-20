## ADDED Requirements

### Requirement: Sync comments to a pull request

When the resolved target is a pull request, the system SHALL post the page's open
Site Review comments to that PR as a review, preserving each comment's text and a
reference to the element it anchors (slug and page URL).

#### Scenario: Post comments to a PR
- **WHEN** the user triggers a sync and the target is PR `#N`
- **THEN** the system posts the open comments to PR `#N` and reports how many were
  synced along with links to the created GitHub content

#### Scenario: Comment carries element context
- **WHEN** a comment anchored to element slug `dancing-gorilla` is synced
- **THEN** the posted GitHub content includes the comment text and identifies the
  element by its slug and the reviewed page URL

### Requirement: Append comments to an existing issue

When the user chooses an existing issue as the target, the system SHALL append the
page's open comments to that issue as a comment.

#### Scenario: Append to selected issue
- **WHEN** the user selects existing issue `#K` and triggers a sync
- **THEN** the system adds a comment to issue `#K` containing the page's open
  Site Review comments and reports the created comment link

### Requirement: Create a new issue from comments

When the user chooses to create a new issue, the system SHALL create an issue in
the connected repository whose title and body are built from the page's open
comments.

#### Scenario: Create issue from comments
- **WHEN** the user chooses "create new issue" and triggers a sync
- **THEN** the system creates an issue in the connected repo containing the page's
  open comments and reports the new issue number and link

#### Scenario: Nothing to sync
- **WHEN** the page has no open comments
- **THEN** the system does not create any GitHub content and reports that there
  was nothing to sync

### Requirement: Idempotent, non-duplicating sync

The system SHALL record what has already been synced so that re-running a sync for
the same page and target does not post duplicate GitHub content for comments that
were already synced.

#### Scenario: Re-sync with no new comments
- **WHEN** the user syncs a page/target that has already been fully synced and no
  comments changed
- **THEN** the system posts no new GitHub content and reports zero newly-synced
  comments

#### Scenario: Re-sync after adding a comment
- **WHEN** a page previously synced gains a new open comment and the user syncs
  again to the same target
- **THEN** the system posts only the new comment and reports one newly-synced
  comment

### Requirement: Sync requires an authenticated connection and a target

The system SHALL refuse to sync when the user is not authenticated to GitHub or no
repository is connected for the page.

#### Scenario: Sync without authentication
- **WHEN** a sync is requested but no valid GitHub token is stored
- **THEN** the system refuses the sync with an unauthenticated error and creates
  no GitHub content

#### Scenario: Sync without a connected repo
- **WHEN** a sync is requested for a page with no connected repository
- **THEN** the system refuses the sync and reports that a repository must be
  connected first
