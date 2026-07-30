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

### Requirement: Shared page furniture is shared

The page chrome that every page hand-rolls SHALL be defined once.

#### Scenario: The back link and footer are not copied per page
- **WHEN** a page renders its navigation back to the landing and its footer
- **THEN** it uses shared markup rather than its own copy

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
