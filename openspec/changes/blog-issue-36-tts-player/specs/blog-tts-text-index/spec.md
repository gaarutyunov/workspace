## ADDED Requirements

**The foundation. Every other capability depends on word identity being minted
exactly once (design D3), so that the text handed to a speech engine and the DOM
being highlighted are the same objects rather than two tokenizations that agree
today.**

### Requirement: Every spoken prose word carries a stable index in the rendered HTML

The build SHALL wrap each spoken word of a post's prose in an element carrying a
post-unique, monotonically increasing index.

#### Scenario: A word can be addressed from script
- **WHEN** a post page is rendered
- **THEN** each spoken word is an element bearing an index attribute
- **AND** the index is unique within the post and increases in reading order

#### Scenario: Indices are assigned by the build, not by the browser
- **WHEN** the same post is rendered twice from unchanged source
- **THEN** the same words carry the same indices, because a browser-side
  tokenizer would have to be kept in agreement with the build's tokenizer forever

#### Scenario: Wrapping does not disturb the article's layout
- **WHEN** words are wrapped
- **THEN** no new direct child of the prose container is introduced, because the
  stylesheet establishes vertical rhythm through an adjacent-sibling rule on the
  prose container's children
- **AND** the rendered article's spacing is unchanged from before this feature

### Requirement: Non-prose content is excluded from speech and from indexing

Content that would be nonsense when read aloud SHALL be excluded from both the
word index and the spoken text.

#### Scenario: Code is not read aloud
- **WHEN** a post contains a fenced code block or an inline code span
- **THEN** its text receives no word index and does not appear in the spoken text

#### Scenario: Decorative and icon content is skipped
- **WHEN** an element is an SVG, or is marked as hidden from assistive technology
- **THEN** its text receives no word index and is not spoken

#### Scenario: An author can opt content out explicitly
- **WHEN** an element is marked with the documented skip attribute
- **THEN** that element and its descendants receive no word index and are not spoken

#### Scenario: Exclusion is proven against content that exercises it
- **WHEN** the exclusion rules are verified
- **THEN** they are verified against a post containing a code fence, an inline
  code span, a link and an image, because the only post in the collection today
  contains none of these and would prove nothing

### Requirement: Headings and the article title are spoken in place

Structural text a reader would expect to hear SHALL be spoken.

#### Scenario: Headings are read
- **WHEN** a post contains headings
- **THEN** their text is indexed and spoken in document order alongside the body

#### Scenario: The title is spoken first
- **WHEN** a post is played
- **THEN** the article title is spoken before the body, even though the title is
  rendered outside the prose container

#### Scenario: Metadata is not read
- **WHEN** a post is played
- **THEN** the publication date and tag list are not spoken

### Requirement: Prose is segmented into sentences

The index SHALL record sentence boundaries, because the speech engine synthesises
and measures one sentence at a time.

#### Scenario: Sentences are ranges over words
- **WHEN** the index is produced
- **THEN** each sentence is expressed as a contiguous range of word indices,
  so a word can be resolved to its sentence and a sentence to its words

#### Scenario: Every word belongs to exactly one sentence
- **WHEN** the index is produced
- **THEN** the sentence ranges cover every indexed word exactly once, with no
  gaps and no overlaps

#### Scenario: A block boundary ends a sentence
- **WHEN** a paragraph, heading or list item ends without terminal punctuation
- **THEN** a sentence boundary is placed there anyway, so that a heading is not
  merged into the paragraph that follows it

### Requirement: A post's spoken text is retrievable without loading its page

The build SHALL publish each post's word list and sentence ranges as a static
resource.

#### Scenario: The queue can play a post the reader is not looking at
- **WHEN** the player needs the text of a post other than the current page
- **THEN** it retrieves that post's word list and sentence ranges as static data,
  without navigating to the post

#### Scenario: The resource is generated at build time
- **WHEN** the site is built
- **THEN** the resource for every post page is emitted as part of the static
  output, requiring no server at runtime

#### Scenario: The resource set matches the page set
- **WHEN** a post has a page but is excluded from the index listing
- **THEN** it still has a text resource, so that the set of playable posts and
  the set of published pages cannot diverge

#### Scenario: The resource is fetched through the configured base path
- **WHEN** the player requests a post's text resource
- **THEN** the request is built from the site's configured base path, because
  pull-request previews are served from a subpath of the same origin and an
  absolute path would fail there

### Requirement: The indices in the page and in the resource are identical

The two consumers of the index SHALL be produced by the same pass.

#### Scenario: The DOM and the resource agree
- **WHEN** a post's page and its text resource are both generated
- **THEN** word index *N* in the resource is the same word as the element bearing
  index *N* on the page

#### Scenario: Divergence is impossible rather than tested for
- **WHEN** the implementation is reviewed
- **THEN** there is exactly one tokenizer, and both outputs derive from one
  traversal of the post, rather than two implementations checked against each other
