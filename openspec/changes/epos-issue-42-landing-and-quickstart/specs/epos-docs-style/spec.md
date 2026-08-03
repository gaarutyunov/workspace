## ADDED Requirements

### Requirement: Adjacent notes and code blocks are separated site-wide

The shared layout SHALL supply external spacing for the kit's block-level
components, because the components themselves set none.

#### Scenario: The note component has no margin of its own
- **WHEN** the kit's note component renders
- **THEN** it is a block with zero external margin, so two adjacent notes touch
  unless the page supplies spacing

#### Scenario: One rule covers every page
- **WHEN** the spacing is added
- **THEN** it lives in the shared layout's global style block, so all four pages
  get it including the two that are generated

#### Scenario: Per-page duplication is removed
- **WHEN** the shared spacing is in place
- **THEN** the per-page rule that spaced code blocks is removed rather than left
  to fight it

#### Scenario: Spacing comes from the token scale
- **WHEN** the spacing is declared
- **THEN** it uses the kit's spacing tokens rather than an ad-hoc length

### Requirement: The site uses the tokens it imports

Every design value on the site SHALL come from a token that exists in the imported
token sheet, and no fallback SHALL contradict the house palette.

#### Scenario: The non-existent muted token is corrected
- **WHEN** the pages are searched for the muted-foreground custom property they
  reference today
- **THEN** that property is not there, because it does not exist in the token
  sheet and every use of it has been changed to the real muted token

#### Scenario: The accent fallback matches the accent
- **WHEN** the layout declares a fallback for the accent colour
- **THEN** the fallback is the house accent, not a different blue

#### Scenario: The house typeface is applied
- **WHEN** the site renders
- **THEN** body text uses the token sheet's sans-serif family rather than a
  hand-written system-font stack, and monospace text uses its mono family

#### Scenario: A fallback that is reachable is not a fallback that is wrong
- **WHEN** a token reference carries a literal fallback
- **THEN** the fallback equals the token's own value in the token sheet

### Requirement: The generated references stay generated

The CLI reference and the Skillfile reference SHALL continue to be produced by the
documentation generator from the code they document, and SHALL NOT be replaced by,
converted to, or partially overridden with hand-authored content. Where the
generator cannot yet express something this change needs, the generator SHALL gain
that capability.

#### Scenario: No generated page becomes hand-authored
- **WHEN** the change is complete
- **THEN** both reference pages are still emitted by the generator from the
  command tree and the instruction table, and neither has been moved out of the
  generator or forked into a maintained-by-hand copy

#### Scenario: The drift gate stays
- **WHEN** the change is complete
- **THEN** continuous integration still re-runs the generator and still fails on
  any diff, and no page has been exempted from that check

#### Scenario: New chrome reaches the generated pages through the generator
- **WHEN** the shared page furniture gains an element the generated pages need
- **THEN** the generator is extended to emit it, rather than the element being
  confined to the hand-written pages

#### Scenario: The generated pages carry per-page data the generator already holds
- **WHEN** a reference page renders its aside
- **THEN** its contents are derived from what the generator already knows about
  that page, not hand-listed

### Requirement: The generated pages are restyled through their generators

Style changes to the CLI reference and the Skillfile reference SHALL be made in the
Go code that emits them, and the generated output SHALL be regenerated and
committed.

#### Scenario: The Astro files are not hand-edited
- **WHEN** the two generated pages change
- **THEN** the change is to the Go source that renders them, and the pages are
  the generator's output

#### Scenario: The drift gate passes
- **WHEN** continuous integration re-runs the generator
- **THEN** it produces no diff against the committed pages

#### Scenario: The generated pages get the same corrections
- **WHEN** the token corrections are applied
- **THEN** the style blocks emitted by the generators carry them too, so the
  reference pages are not the only off-palette pages on the site

### Requirement: Every page below the landing carries a breadcrumb

Each documentation page SHALL open with a breadcrumb trail above its title, in one
shared form, and the landing SHALL carry none.

#### Scenario: Where the breadcrumb sits
- **WHEN** a documentation page renders
- **THEN** a breadcrumb trail appears above the page title, between the site
  header and that title, and nothing else separates them

#### Scenario: The landing has no breadcrumb
- **WHEN** the landing renders
- **THEN** it carries no breadcrumb, because it is the root of the trail

#### Scenario: Two crumbs, the last one plain
- **WHEN** a breadcrumb renders
- **THEN** it shows the site root as a link followed by the current page's own
  title, and the current page's crumb is plain text in the foreground colour
  rather than a link to itself

#### Scenario: The separator is a slash
- **WHEN** the crumbs render
- **THEN** they are separated by a forward slash with equal spacing on both
  sides, taking the muted colour of the trail rather than a colour of its own

#### Scenario: The trail is monospace at body-small size
- **WHEN** a breadcrumb renders
- **THEN** it uses the monospace family at the small body size in the muted
  foreground colour, matching the reference site's curriculum-vitae page and not
  its dimmer, smaller skill-page variant

#### Scenario: The link responds to the pointer
- **WHEN** the pointer enters the root crumb
- **THEN** it transitions to the full foreground colour

#### Scenario: The breadcrumb is announced as navigation
- **WHEN** a screen reader reaches the breadcrumb
- **THEN** it encounters a labelled navigation landmark, the current page's crumb
  is marked as the current page, and the separator is hidden from the
  accessibility tree so it is not read aloud between crumbs

#### Scenario: One definition, four pages
- **WHEN** the breadcrumb renders on any page
- **THEN** it comes from a single shared definition, and no page carries its own
  copy of the markup

#### Scenario: The generated pages get it from the generator
- **WHEN** a generated reference page renders its breadcrumb
- **THEN** the generator emits it from that page's own title, and the drift check
  still passes

#### Scenario: It replaces the hand-rolled back link
- **WHEN** the breadcrumb is in place
- **THEN** the per-page "back to the landing" link is removed, because the root
  crumb is that link

### Requirement: One page shell, with the content column set by a grid

Every page SHALL render inside the same container width as the reference site,
and the documentation pages SHALL take their reading measure from a
content-and-aside grid rather than from a narrower container.

#### Scenario: One container width for every page
- **WHEN** any page renders on a wide viewport
- **THEN** its container is the reference site's width — the same on the landing
  and on every documentation page — with the reference site's responsive
  gutters, and no page opts into a different width

#### Scenario: The documentation pages split into content and aside
- **WHEN** a documentation page renders above the large breakpoint
- **THEN** its body is a twelve-column grid with the content in nine columns and
  an aside in three, matching the reference site's inner pages

#### Scenario: The reading measure does not regress
- **WHEN** the content column is measured at the container's maximum width
- **THEN** it is no wider than the measure the documentation pages had before this
  change

#### Scenario: It stacks on a narrow viewport
- **WHEN** a documentation page renders below the large breakpoint
- **THEN** the aside stacks below the content and neither is clipped

#### Scenario: The aside carries within-page navigation
- **WHEN** a documentation page's aside renders
- **THEN** it offers navigation within the page and to the sibling documentation
  pages, which is what the long reference pages have none of today

#### Scenario: The header is the reference site's
- **WHEN** any page renders
- **THEN** the site header is sticky to the top of the viewport at the reference
  site's height, over the opaque page background, with no border and no blur

### Requirement: Inner-page typography follows the reference site, and extends it only where it must

Page titles, section headings, lists and key/value rows SHALL follow the reference
site's inner pages. Where the reference site has no pattern for something a
documentation site needs, the extension SHALL be derived from the existing scale
and SHALL be identified as an extension.

#### Scenario: The page title is visible
- **WHEN** a documentation page renders
- **THEN** its title is a visible heading at the reference site's inner-page
  title size, weight and negative tracking — not the visually hidden heading the
  landing uses

#### Scenario: Section headings are the shared label pattern
- **WHEN** a section heading renders inside a documentation page
- **THEN** it uses the same monospace, uppercase, un-letter-spaced label pattern
  the landing uses, with no separate inner-page variant

#### Scenario: Bullets are em-dashes
- **WHEN** a list renders
- **THEN** each item is led by an em-dash rather than a list marker, matching the
  reference site

#### Scenario: Key and value rows are ruled
- **WHEN** a two-column key/value list renders
- **THEN** each row carries a hairline rule beneath it, with the key in the
  foreground colour and the value in muted monospace

#### Scenario: What the reference site does not have is named as an extension
- **WHEN** the documentation pages use a sub-section heading, a code block, or a
  table
- **THEN** those are acknowledged as having no counterpart on the reference site,
  and their treatment is derived from the scale already in use rather than
  imported from elsewhere

#### Scenario: Divergences in the reference site are not reproduced
- **WHEN** the reference site's two inner pages disagree — on gutters, on grid
  gap, or on the breadcrumb's font, size and colour
- **THEN** this site picks one value and applies it everywhere, rather than
  carrying both

### Requirement: Shared page furniture is shared

The page chrome that every page hand-rolls SHALL be defined once.

#### Scenario: The navigation and footer are not copied per page
- **WHEN** a page renders its navigation back to the landing and its footer
- **THEN** it uses shared markup rather than its own copy — the navigation being
  the shared breadcrumb, which is the only such link on the page

#### Scenario: The footer stays, even though the reference site has none
- **WHEN** a page renders
- **THEN** it still carries a footer, because a documentation site needs the
  repository and licence links a personal site does not — this is a deliberate
  departure from the reference site rather than an oversight

#### Scenario: The section-label pattern is defined once
- **WHEN** a page renders a section label
- **THEN** it uses the one shared definition of that pattern

#### Scenario: The refactor does not change the generated pages' text
- **WHEN** the furniture is shared and the generators are re-run
- **THEN** the reference pages' documentary content is byte-identical to before,
  and only their chrome and style blocks differ

### Requirement: The site remains correct under its base path and in dark

The site SHALL keep working when served from a sub-path, and SHALL remain
dark-themed with the light theme left as the kit's unused opt-in.

#### Scenario: Every internal link goes through the base-path helper
- **WHEN** a page links to another page or an asset
- **THEN** it composes the URL from the layout's base-path helper, so a preview
  build under a pull-request sub-path resolves

#### Scenario: A preview build resolves
- **WHEN** the site is built with the pull-request preview base path
- **THEN** its links and assets resolve under that path

#### Scenario: Dark is the only theme shipped
- **WHEN** the site renders
- **THEN** it renders dark regardless of the viewer's system preference, matching
  the reference site, and no page sets the light-theme attribute
