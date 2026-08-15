## ADDED Requirements

**The issue's last feature: *"save the last position that was played and highlight
it + move to it if reloaded"*. The site is a multi-page static site, so a reload
or a navigation tears down the player; this capability is what makes that
survivable.**

### Requirement: Playback position is saved

#### Scenario: Position is recorded as playback proceeds
- **WHEN** a post is playing
- **THEN** the current post and word position are saved as playback advances

#### Scenario: Position is recorded when the page goes away
- **WHEN** the reader navigates away, reloads, or the tab is hidden
- **THEN** the current position is saved before the page is torn down

#### Scenario: Position is recorded on pause
- **WHEN** the reader pauses
- **THEN** the position is saved

### Requirement: The saved position is restored on return

#### Scenario: The last-played word is marked
- **WHEN** a reader opens a post that holds the saved position
- **THEN** that word is visually marked as where they left off, distinguishably
  from the active playing highlight

#### Scenario: The view moves to the saved position
- **WHEN** a post with a saved position is opened
- **THEN** the page moves to that position

#### Scenario: The marked position clears the sticky header
- **WHEN** the page moves to the saved position
- **THEN** the marked word is not left underneath the site's sticky header

#### Scenario: Reduced motion is respected
- **WHEN** the reader has requested reduced motion
- **THEN** the view moves without animation, overriding the site's global
  smooth-scroll setting

#### Scenario: Restoring does not start playback
- **WHEN** a post with a saved position is opened
- **THEN** nothing plays until the reader asks it to, and resuming continues from
  the saved position rather than the top

#### Scenario: The mark is cleared once superseded
- **WHEN** playback resumes past the saved position
- **THEN** the resume mark is removed so it is not confused with the live highlight

### Requirement: Queue and preferences survive a reload

#### Scenario: The queue is restored
- **WHEN** a reader reloads or navigates
- **THEN** the queue and its order are as they were

#### Scenario: Preferences are restored
- **WHEN** a reader returns
- **THEN** the chosen engine, voice and speaking rate are as they were

### Requirement: Preview deployments do not corrupt production state

The site's pull-request previews are served from a subpath of the production
origin, so they share storage with it.

#### Scenario: Preview state is isolated
- **WHEN** a reader uses the player on a preview deployment
- **THEN** the production site's saved position, queue and preferences are unaffected

#### Scenario: Production state is isolated from previews
- **WHEN** a reader uses the player on the production site
- **THEN** a preview deployment's state is unaffected

### Requirement: Stored state is handled defensively

#### Scenario: Unreadable state is discarded, not fatal
- **WHEN** stored state is missing, malformed, or from an incompatible version
- **THEN** it is discarded and the player starts clean, without throwing

#### Scenario: The position no longer exists in the post
- **WHEN** a saved word position is beyond the end of a post that has since been
  edited
- **THEN** the position is clamped to a valid one rather than failing to restore

#### Scenario: Storage is unavailable
- **WHEN** the browser denies access to persistent storage
- **THEN** the player still plays, without persistence, rather than failing to start
