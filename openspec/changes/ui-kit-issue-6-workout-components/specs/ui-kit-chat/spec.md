## ADDED Requirements

### Requirement: Message bubble with roles

The kit SHALL provide a `ga-chat-message` element that renders one message of a
conversation, styled by the role of its author.

#### Scenario: User and assistant messages are distinguishable
- **WHEN** messages with the user role and the assistant role are rendered
- **THEN** they are visually distinct (alignment and surface treatment) and the
  role is exposed to assistive technology

#### Scenario: Application-rendered content
- **WHEN** an application slots already-rendered content (e.g. markdown it
  converted itself) into a message
- **THEN** the bubble renders that content without transforming it

#### Scenario: Author and timestamp
- **WHEN** an author name and/or a timestamp is supplied
- **THEN** the message renders them as a header without disturbing the body
  layout

### Requirement: Message delivery states

`ga-chat-message` SHALL render the state of a message so an in-flight or failed
answer is distinguishable from a delivered one.

#### Scenario: Pending message
- **WHEN** a message is marked pending
- **THEN** it renders a waiting indicator in place of the body

#### Scenario: Streaming message
- **WHEN** a message is marked streaming and its content grows
- **THEN** it renders the content received so far together with an indication
  that more is coming

#### Scenario: Failed message
- **WHEN** a message is marked as failed
- **THEN** it is rendered in the kit's error treatment and the failure is
  announced

### Requirement: Conversation transcript

The kit SHALL provide a `ga-chat` element that lays out a scrolling transcript of
messages with optional header and composer areas.

#### Scenario: Rendering a conversation
- **WHEN** messages are placed inside the transcript
- **THEN** they are laid out in order in a scrollable region sized to the
  container

#### Scenario: Following new messages
- **WHEN** a message is appended while the transcript is scrolled to the bottom
- **THEN** the transcript scrolls to keep the newest message visible

#### Scenario: Not stealing the reader's place
- **WHEN** the user has scrolled up to read earlier messages and a new message
  arrives
- **THEN** the transcript does not scroll away from what the user is reading

#### Scenario: Jump to latest appears when the reader is behind
- **WHEN** the user has scrolled up away from the newest message
- **THEN** `ga-chat` shows a "jump to latest" control, provided by the element
  itself rather than the application

#### Scenario: Jump to latest returns to following
- **WHEN** the user activates the jump-to-latest control
- **THEN** the transcript scrolls to the newest message and resumes following
  appended messages

#### Scenario: Hidden when there is nothing to jump to
- **WHEN** the transcript is scrolled to the bottom
- **THEN** the jump-to-latest control is not shown

#### Scenario: Unread arrivals are signalled
- **WHEN** messages arrive while the user is scrolled up
- **THEN** the jump-to-latest control indicates that newer messages are waiting

#### Scenario: Reachable by keyboard
- **WHEN** the jump-to-latest control is shown and the user navigates by keyboard
- **THEN** it is focusable and activates with the keyboard, and it is announced by
  a screen reader

#### Scenario: Empty conversation
- **WHEN** the transcript contains no messages
- **THEN** it renders its empty state rather than a blank area

### Requirement: Composer built from existing kit elements

The composer SHALL be a documented composition of the kit's existing input and
button elements rather than a new bespoke input.

#### Scenario: Composer recipe
- **WHEN** a developer follows the documented recipe
- **THEN** a composer built from the kit's existing input and button elements
  sits in the transcript's footer area and submits on both button activation and
  the keyboard submit gesture
