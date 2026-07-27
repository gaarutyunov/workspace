## ADDED Requirements

### Requirement: A review comment

The kit SHALL provide a comment element carrying an author, a timestamp, a body,
a resolution state and an optional anchor describing what is being commented on.

#### Scenario: Author and time
- **WHEN** a comment declares an author and a timestamp
- **THEN** both are rendered subordinate to the body, and the timestamp is
  machine-readable as well as human-readable

#### Scenario: Uniform alignment
- **WHEN** several comments from different authors are rendered together
- **THEN** they are aligned and styled identically — a review thread has no
  "mine versus theirs" axis

#### Scenario: A resolved comment is visibly settled
- **WHEN** a comment is marked resolved
- **THEN** it is de-emphasised while remaining readable, and its state is
  conveyed to assistive technology rather than by styling alone

#### Scenario: Resolving is reversible
- **WHEN** the resolution control is activated on a resolved comment
- **THEN** it reopens, and the component emits an event naming the new state

#### Scenario: An anchor target
- **WHEN** a comment declares what it is anchored to
- **THEN** that target is shown with the comment

### Requirement: A thread of comments with a composer

The kit SHALL provide a container for comments that includes a composer for
adding one.

#### Scenario: It is a list, not a live log
- **WHEN** the thread is read by assistive technology
- **THEN** it is announced as a list of comments — not as a live region that
  re-announces itself as entries arrive

#### Scenario: Adding a comment does not move the reader
- **WHEN** a comment is added while the reader is looking at an earlier one
- **THEN** the scroll position is left alone

#### Scenario: The composer submits
- **WHEN** the composer is submitted, by its control or by its keyboard
  shortcut
- **THEN** the component emits an event carrying the text, and does not clear
  the field until the host says the comment was accepted

#### Scenario: The composer states its target
- **WHEN** the thread is anchored to something
- **THEN** the composer says what a new comment will attach to

#### Scenario: An empty thread
- **WHEN** a thread has no comments
- **THEN** it shows an empty state and still offers the composer

### Requirement: The chat components are not repurposed

The comment thread SHALL be its own component, and the chat components SHALL be
left as they are.

#### Scenario: Chat is unchanged
- **WHEN** the chat components are used after this change
- **THEN** they behave exactly as before, with their speaker vocabulary
  untouched

#### Scenario: The distinction is documented
- **WHEN** a developer reads either component's page
- **THEN** it states that a conversation between two parties uses chat, and a
  review thread uses the comment thread, with the reason given
