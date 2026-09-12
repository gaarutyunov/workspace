## ADDED Requirements

**The blog has no lint, no typecheck and no tests: a successful build is its
entire gate. This change lands the repository's first substantial client-side
application, so a check comes with it (design D14) rather than after it.**

### Requirement: Pull requests are type-checked

#### Scenario: Type errors fail the pull request
- **WHEN** a pull request introduces a type error in the site's source
- **THEN** continuous integration fails, rather than deploying a preview and
  reporting success

#### Scenario: The check runs before the build
- **WHEN** a pull request's workflow runs
- **THEN** type checking runs ahead of the build, so a type error is reported as
  such rather than as a build failure

#### Scenario: The check is runnable the same way locally
- **WHEN** a contributor wants to reproduce the check
- **THEN** a single documented package script runs exactly what continuous
  integration runs

### Requirement: Pre-existing type errors are fixed, not suppressed

#### Scenario: Existing files are checked too
- **WHEN** type checking is introduced
- **THEN** it covers the files that already exist, not only the new ones

#### Scenario: Errors it surfaces are resolved in this change
- **WHEN** type checking surfaces errors in pre-existing code
- **THEN** they are fixed within this change, rather than excluded, ignored, or
  deferred to follow-up work

### Requirement: The player's browser behaviour is verified on a real deployment

The project has no test framework and no browser-automation harness, and the
development machine has no Node runtime, so verification SHALL be defined
explicitly rather than assumed.

#### Scenario: Verification happens against the deployed preview
- **WHEN** the change is verified
- **THEN** it is exercised on the pull request's deployed preview in a real
  browser, because nothing in the project can run the site locally

#### Scenario: Both engines are exercised
- **WHEN** the player is verified
- **THEN** both the browser voice and the neural voice are exercised, including
  the neural voice's download path

#### Scenario: Performance claims are measured
- **WHEN** the change reports whether the neural engine is viable without GPU
  acceleration
- **THEN** the figure is measured on the preview and recorded, rather than taken
  from published benchmarks that assume a different backend

#### Scenario: The page-weight cost is measured
- **WHEN** per-word markup is added to every post
- **THEN** the resulting change in compressed page size is measured on the preview
  and recorded
