## ADDED Requirements

**The issue's second and third features: *"add to queue button to play next"* and
*"functionality to reorder the queue"*. The queue plays without navigating (design
D10) — it is driven by each post's static text resource, not by loading pages.**

### Requirement: Posts can be added to a play queue

#### Scenario: Adding from the list
- **WHEN** a reader activates the add-to-queue control on a post in the list
- **THEN** the post is appended to the queue, and playback of the current post is
  not interrupted

#### Scenario: Adding from a post page
- **WHEN** a reader adds the post they are reading to the queue
- **THEN** it is appended to the queue

#### Scenario: Play next
- **WHEN** a reader chooses to play a post next
- **THEN** it is placed immediately after the currently playing item rather than
  at the end

#### Scenario: A post is not queued twice
- **WHEN** a reader adds a post already present in the queue
- **THEN** the queue still contains that post exactly once, and the reader is not
  left wondering whether the action registered

#### Scenario: Adding is confirmed
- **WHEN** a post is added to the queue
- **THEN** the reader receives feedback that it was added

### Requirement: The queue advances automatically without navigation

#### Scenario: The next post plays when the current one ends
- **WHEN** a post finishes and the queue is not empty
- **THEN** the next post begins playing

#### Scenario: Advancing does not require being on the post's page
- **WHEN** the queue advances to a post the reader is not viewing
- **THEN** that post plays regardless, because its spoken text is available as a
  static resource

#### Scenario: The queue ends cleanly
- **WHEN** the last queued post finishes
- **THEN** playback stops and the player reports that the queue is finished

#### Scenario: A failing item does not stall the queue
- **WHEN** a queued post's text cannot be retrieved
- **THEN** the failure is reported and the queue advances to the next item

### Requirement: The queue can be inspected and reordered

#### Scenario: The queue is viewable
- **WHEN** a reader opens the queue
- **THEN** the queued posts are listed in play order, with the current item marked

#### Scenario: Reordering by explicit controls
- **WHEN** a reader moves a queued post up or down
- **THEN** the queue order changes accordingly and playback of the current item is
  not interrupted

#### Scenario: Reordering is operable by keyboard and touch
- **WHEN** a reader uses only the keyboard, or a touch device
- **THEN** they can reorder the queue, because a drag-only affordance would be the
  least accessible control on the site

#### Scenario: Dragging, where offered, is an addition rather than the mechanism
- **WHEN** drag-based reordering is present
- **THEN** the explicit move controls remain available and functional

#### Scenario: Removing an item
- **WHEN** a reader removes a queued post
- **THEN** it is dropped from the queue

#### Scenario: Removing the item being played
- **WHEN** the reader removes the currently playing post
- **THEN** playback advances to the next queued post, or stops if none remains

#### Scenario: Clearing the queue
- **WHEN** a reader clears the queue
- **THEN** the queue is emptied and playback stops

### Requirement: The queue behaves correctly at its edges

The blog contains a single published post today, so the degenerate cases are the
common cases and SHALL be handled rather than discovered later.

#### Scenario: An empty queue
- **WHEN** nothing is queued
- **THEN** the queue view says so, and no control implies a next item exists

#### Scenario: A single-item queue
- **WHEN** exactly one post is queued
- **THEN** reorder controls that cannot do anything are disabled rather than
  present but inert

#### Scenario: The first and last items
- **WHEN** the first item cannot move up, or the last cannot move down
- **THEN** the corresponding control is disabled

#### Scenario: A queued post no longer exists
- **WHEN** a restored queue names a post that is no longer published
- **THEN** that entry is dropped without breaking the rest of the queue
