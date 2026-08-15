## ADDED Requirements

**The reader-facing surface: a persistent player, and per-post controls on the
list. The issue's first feature — *"play directly from the list of blogs"* — is
here.**

### Requirement: A player is present on every page of the blog

The player SHALL be mounted site-wide, not only on post pages.

#### Scenario: The player is reachable from the list
- **WHEN** a reader is on the index page
- **THEN** the player is available without navigating to a post

#### Scenario: The player is unobtrusive when idle
- **WHEN** nothing is playing and nothing is queued
- **THEN** the player does not occupy reading space

#### Scenario: The player does not obscure content
- **WHEN** the player is visible during playback
- **THEN** it does not cover the end of the article, and its stacking order is
  chosen deliberately with respect to the site's sticky header

### Requirement: A post can be played directly from the list

The index page SHALL offer playback controls per post.

#### Scenario: Playing from the list starts speech without navigation
- **WHEN** a reader activates the play control on a post in the list
- **THEN** that post begins playing, and the reader stays on the list page

#### Scenario: Controls do not hijack the post link
- **WHEN** a reader activates a play or queue control on a list item
- **THEN** the browser does not navigate to the post
- **AND** the control is not nested inside the card's link element, because a
  control inside a link is invalid and would navigate

#### Scenario: The post link still works
- **WHEN** a reader clicks the post card away from the controls
- **THEN** they navigate to the post as before this feature

#### Scenario: The currently playing post is identifiable in the list
- **WHEN** a post is playing
- **THEN** its list entry indicates that it is the one playing

### Requirement: Playback can be started, paused and resumed

#### Scenario: Pause and resume
- **WHEN** a reader pauses and later resumes
- **THEN** speech continues from where it stopped, not from the start of the post

#### Scenario: Skipping within a post
- **WHEN** a reader skips forward or back
- **THEN** playback moves by a whole sentence, and the highlight follows

#### Scenario: Starting a new post replaces the current one
- **WHEN** a reader plays a post while another is playing
- **THEN** the current post stops and the new one starts

#### Scenario: Playback speed is adjustable
- **WHEN** a reader changes the speaking rate
- **THEN** subsequent speech uses the new rate, and the change is remembered

### Requirement: The player identifies what is playing and what is next

#### Scenario: The current item is named
- **WHEN** something is playing
- **THEN** the player shows the post's title

#### Scenario: Progress within the post is shown
- **WHEN** something is playing
- **THEN** the player shows progress through the post

#### Scenario: The engine in use is visible and changeable
- **WHEN** a reader opens the player's controls
- **THEN** the active voice is shown and the alternative can be selected

### Requirement: The player is operable by keyboard and announced to assistive technology

The repository's existing accessibility standard SHALL be met.

#### Scenario: Every control is reachable by keyboard
- **WHEN** a reader navigates with the keyboard
- **THEN** every player and per-post control can be focused and activated, with a
  visible focus indicator

#### Scenario: Every control is labelled
- **WHEN** a control is presented as an icon
- **THEN** it carries an accessible name

#### Scenario: State changes are announced
- **WHEN** playback starts, stops, or an error occurs
- **THEN** the change is announced to assistive technology rather than only
  appearing visually

#### Scenario: Motion preferences are respected
- **WHEN** the reader has requested reduced motion
- **THEN** the player introduces no animated scrolling or transitions

### Requirement: The player is styled from the site's design tokens

#### Scenario: No hard-coded colours
- **WHEN** the player and its controls are styled
- **THEN** colours, spacing, radii and typography come from the site's existing
  design tokens rather than literal values

#### Scenario: The site's component library is used where it fits
- **WHEN** a control has an equivalent in the site's component library
- **THEN** that component is used rather than a bespoke one

### Requirement: Playback failures are visible to the reader

#### Scenario: A post's text cannot be retrieved
- **WHEN** the player cannot retrieve a post's spoken text
- **THEN** it reports the failure and continues with the rest of the queue

#### Scenario: The active engine fails mid-playback
- **WHEN** the active engine fails while playing
- **THEN** the failure is reported and the reader is offered the other engine
