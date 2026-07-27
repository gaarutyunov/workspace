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

The comment thread SHALL be its own component, and the chat components SHALL
keep their behaviour and their vocabulary.

#### Scenario: Chat behaviour is unchanged
- **WHEN** the chat components are used after this change
- **THEN** they behave exactly as before — same layout, same speaker
  vocabulary, same scroll-follow

#### Scenario: The distinction is documented
- **WHEN** a developer reads either component's page
- **THEN** it states that a conversation between two parties uses chat, and a
  review thread uses the comment thread, with the reason given

### Requirement: A chat message's speaker is not an ARIA role

The attribute naming a chat message's speaker SHALL NOT collide with the global
ARIA `role` attribute.

#### Scenario: The speaker is declared under its own name
- **WHEN** a chat message declares who spoke
- **THEN** it does so through an attribute of its own, not through `role`

#### Scenario: The host does not claim an ARIA role by accident
- **WHEN** a chat message is inspected
- **THEN** its host element does not carry an ARIA `role` it did not intend —
  which matters because some speaker names are also real ARIA roles

#### Scenario: The vocabulary is unchanged
- **WHEN** the speaker is set
- **THEN** the accepted values are the same as before; only the attribute name
  differs

#### Scenario: The break is documented
- **WHEN** the release carrying this change is published
- **THEN** its notes state that the attribute was renamed, name the old and new
  spelling, and say which released version carried the old one
