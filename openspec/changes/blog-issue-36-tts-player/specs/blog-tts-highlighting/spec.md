## ADDED Requirements

**The issue's hardest feature: *"highlight the words playing currently"*. No
in-browser model emits word timings (design D1/D4), so this capability commits to
two different guarantees and is explicit about which is which. Sentence-level
accuracy is a promise; word-level accuracy is best-effort.**

### Requirement: The sentence being spoken is always highlighted accurately

Sentence-level highlighting SHALL be exact, on every engine.

#### Scenario: The spoken sentence is marked
- **WHEN** a post is playing on the page the reader is viewing
- **THEN** the sentence currently being spoken is visually distinguished

#### Scenario: Sentence timing is measured, not estimated
- **WHEN** a sentence's audio is produced
- **THEN** its duration is taken from the audio itself, so sentence boundaries do
  not drift over the length of a post

#### Scenario: Error does not accumulate
- **WHEN** playback has run for several minutes
- **THEN** the highlighted sentence is still the sentence being spoken, because
  any within-sentence error is discarded at each boundary

### Requirement: The word being spoken is highlighted on a best-effort basis

#### Scenario: Word highlighting from real timings
- **WHEN** the active engine supplies word-level timing
- **THEN** the highlighted word is the word being spoken

#### Scenario: Word highlighting from estimated timings
- **WHEN** the active engine supplies no word-level timing
- **THEN** the sentence's measured duration is distributed across its words, and
  the estimated word is highlighted

#### Scenario: Estimation is bounded by the sentence
- **WHEN** an estimated word highlight is wrong
- **THEN** it is corrected at the next sentence boundary at the latest

#### Scenario: Degrading rather than misleading
- **WHEN** word position cannot be estimated meaningfully for a passage
- **THEN** only the sentence is highlighted, rather than a word chosen arbitrarily

### Requirement: Highlighting is driven by the audio clock

#### Scenario: Position comes from the audio
- **WHEN** the highlight advances
- **THEN** its position is derived from the audio playback clock rather than from
  a timer started alongside it

#### Scenario: Pausing freezes the highlight
- **WHEN** playback is paused
- **THEN** the highlight stops on the current word and does not continue advancing

#### Scenario: Seeking moves the highlight
- **WHEN** the reader skips to another sentence
- **THEN** the highlight moves there immediately

#### Scenario: Rate changes do not desynchronise the highlight
- **WHEN** the reader changes the speaking rate
- **THEN** the highlight remains aligned with the audio

### Requirement: Highlighting applies only to the post being viewed

#### Scenario: Playing a post the reader is not viewing
- **WHEN** the playing post is not the page on screen
- **THEN** no highlighting is applied to the page, and playback continues normally

#### Scenario: Arriving at the playing post
- **WHEN** the reader opens the post that is currently playing
- **THEN** highlighting attaches at the correct position without restarting playback

### Requirement: The reader can follow along without chasing the highlight

#### Scenario: Auto-scroll follows the spoken text
- **WHEN** the highlighted word moves out of view during playback
- **THEN** the page brings it back into view

#### Scenario: Auto-scroll clears the sticky header
- **WHEN** the page scrolls to the highlighted word
- **THEN** the word is not left underneath the site's sticky header

#### Scenario: The reader's own scrolling wins
- **WHEN** the reader scrolls manually during playback
- **THEN** auto-scroll yields until the reader returns, rather than fighting them

#### Scenario: Reduced motion is respected
- **WHEN** the reader has requested reduced motion
- **THEN** the view changes without smooth scrolling, overriding the site's global
  smooth-scroll setting

### Requirement: The highlight is legible and non-destructive

#### Scenario: Styled from design tokens
- **WHEN** the highlight is styled
- **THEN** it derives from the site's existing tokens rather than literal colours,
  so it survives a theme change

#### Scenario: Sufficient contrast
- **WHEN** a word is highlighted
- **THEN** the word remains legible against the highlight

#### Scenario: Text does not move when highlighted
- **WHEN** the highlight is applied or removed
- **THEN** no reflow occurs — line breaks and article layout are unchanged

#### Scenario: Selection and links still work
- **WHEN** a reader selects text or clicks a link inside highlighted prose
- **THEN** selection and link behaviour are unaffected
