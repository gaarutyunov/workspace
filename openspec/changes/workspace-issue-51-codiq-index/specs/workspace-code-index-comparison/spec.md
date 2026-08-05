## ADDED Requirements

### Requirement: The comparison is pre-registered before either system is run

The workspace SHALL commit, before running either code-graph system, the corpus
pinned to exact commits, the question set, the exact operation each system is
asked to perform for each question, the expected answer for each question, and
the thresholds that decide the outcome.

The commit that records them SHALL state that it is the pre-registration, so
that its position before the run is verifiable from history rather than
asserted.

#### Scenario: The corpus is pinned

- **WHEN** the pre-registration is read
- **THEN** every repository in the corpus is named with the exact commit it was
  indexed at, so the run can be reproduced

#### Scenario: The questions exist before the results

- **WHEN** the repository's history is inspected
- **THEN** the commit carrying the question set and the answer key precedes
  every commit carrying a measurement

#### Scenario: A question cannot be dropped after the fact

- **WHEN** the report is produced
- **THEN** it reports every pre-registered question, including the ones either
  system answered badly or could not express at all

### Requirement: The answer key is authored from the source, independent of both systems

The expected answer for each question SHALL be derived by reading the pinned
source, SHALL cite repository, path and symbol for every expected element, and
SHALL NOT be taken from the output of either system under comparison.

#### Scenario: A disputed answer can be checked

- **WHEN** a reader disagrees with a score
- **THEN** they can open the cited file at the pinned commit and dispute that
  specific expected element

#### Scenario: Neither system defines correctness

- **WHEN** the two systems disagree on a question
- **THEN** the key decides which is right, and it is possible for both to be
  wrong

### Requirement: Every question is scored on stated metrics

The comparison SHALL record, for each question and each system: whether the
system can express the query at all, the proportion of expected elements
returned, the proportion of returned elements that were expected, the time taken,
and the size of the request and response.

The comparison SHALL record, for each index run: wall-clock time, bytes on disk,
and the proportion of a repository's parseable files that were indexed.

#### Scenario: An inexpressible question is recorded as such

- **WHEN** a system cannot state a question at all
- **THEN** it is recorded as inexpressible rather than as a zero score, because
  the two mean different things

#### Scenario: Answer cost is a number

- **WHEN** the report compares the two surfaces
- **THEN** the cost of an answer appears as a measured request and response size
  per question, not as prose about one surface being more verbose

#### Scenario: Raw per-question results are published

- **WHEN** the report is read
- **THEN** the per-question table is present alongside any aggregate, so an
  aggregate cannot conceal a category that failed

### Requirement: The outcome is decided by a rule fixed in advance

The comparison SHALL state its pass condition per question category before the
run, and the report SHALL apply exactly that rule.

A category whose ceiling is a property of the query surface rather than of the
index SHALL be reported and excluded from the rule, with the reason stated.

#### Scenario: The rule decides the outcome

- **WHEN** the measurements are in
- **THEN** the conclusion follows from the pre-stated thresholds, and no
  threshold was chosen or adjusted after a measurement was seen

#### Scenario: An unfavourable result is reportable

- **WHEN** the thresholds are not met
- **THEN** the report says so and names the failing category, and this is a
  valid completion of the work rather than a reason to revise the rule

#### Scenario: A frozen query is not tuned to its score

- **WHEN** a pre-registered query is found to be wrong rather than merely
  low-scoring
- **THEN** the correction is committed as an amendment carrying its reason, and
  the report gives both the pre-registered and the amended number

### Requirement: Capabilities only one system has are listed, not scored

The comparison SHALL enumerate the capabilities each system has that the other
has no analogue for, and SHALL exclude them from the scored questions.

#### Scenario: The other system is not scored on questions it does not claim

- **WHEN** one system offers a capability the other does not
- **THEN** it appears in the enumeration and contributes to no score

#### Scenario: The enumeration runs in both directions

- **WHEN** the enumeration is read
- **THEN** it lists capabilities unique to each system, not only to one

#### Scenario: Known limits are recorded before the run

- **WHEN** a limit of either surface is known in advance to bound a category
- **THEN** it is recorded in the pre-registration, so the report cannot present
  it as a discovery

### Requirement: The comparison ends in a recommendation about how the workspace uses each system

The report SHALL end with a statement of which system this workspace should
reach for, for which kind of question, and that statement SHALL be reflected in
the workspace's agent instructions.

#### Scenario: The result changes behaviour

- **WHEN** the report is accepted
- **THEN** the workspace instructions say which graph answers which kind of
  question, and the reason traces to a measured category

#### Scenario: A "not yet" is still actionable

- **WHEN** the outcome is that the new system is not yet a viable second source
- **THEN** the report names what would have to change for it to become one
