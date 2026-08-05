Milestone-ordered. Each milestone ends with a **gate**: something executed
against the real stack that would fail if the milestone were wrong. Reading the
diff is never a gate.

Line and file references are to `gaarutyunov/codiq` at `origin/main` `c11e46b`
and `gaarutyunov/gopgql` at `origin/main` `060922e`.

## 0. Before anything — the four owner decisions

Sequenced first because M1 is a data-model change to another repository and
should not be written if Q4 is answered differently.

- [ ] 0.1 Q1 — codiq replaces gortex, or sits beside it. Recommendation:
      **beside**, and the comparison is a characterisation rather than a
      bake-off. Everything below assumes it.
- [ ] 0.2 Q2 — the project list. Recommendation: the eight named in
      `proposal.md`; `postgres-pglite` and `pglite` deferred to a second run.
- [ ] 0.3 Q3 — where Postgres comes from. Recommendation: codiq's own
      `deploy/docker-compose.yml`, unmodified.
- [ ] 0.4 Q4 — the codiq change lands under this issue as its own PR in
      `gaarutyunov/codiq`, or as a separate codiq issue with #51 `Blocked`.
      Recommendation: **under this issue**.

## 1. M1 — codiq gains a corpus  *(repo: `gaarutyunov/codiq`)*

### 1a. Coordinate resolution stops at the repository (design D3, D4)

The load-bearing half. `coord.Resolve` currently walks upward with no bound;
measured on this machine, seven trees under `projects/` resolve to
`/Users/germanarutyunov/package.json`.

- [ ] 1.1 `coord.Resolve` stops at the directory it is given: **the directory
      you index is the repository**. No signature change — both callers
      (`index/index.go:176`, `index/dbos.go:704`) already pass the resolved
      repository root — and no new flag, because there is no second candidate
      for the bound.
- [ ] 1.2 **Compatibility, and state it in the change:** `codiq ./subdir` inside
      a module stops inheriting that module's coordinate and gets a
      corpus-named one instead. `cmd/codiq`'s usage text says the target "must
      be inside a module CodiQ can resolve a package coordinate for (go.mod)";
      that sentence becomes false and is rewritten. Indexing a subdirectory was
      already half-broken — `file.path` was subdirectory-relative while
      `Coord.Root` was the module root, so paths and namespaces were measured
      from different origins — so this narrows a usage that never produced a
      coherent graph rather than removing a working one.
- [ ] 1.3 An ecosystem with no manifest inside the repository resolves to a
      coordinate whose `Name` is the corpus name, not `Unknown`, with `Root` at
      the repository root. `Ecosystem.unknown`'s doc comment is rewritten: it is
      no longer "no name", it is "no *manifest*", and the name now comes from
      the caller.
- [ ] 1.4 `Coord.Prefix` stays four components wide and the `file` table keeps
      four columns. No fifth component (design D4).
- [ ] 1.5 `Unknown` (`.`) keeps its meaning for a **version** and loses it for a
      **name**. Say so in the package doc, because the two were the same value
      for the same reason until now.
- [ ] 1.6 Unit tests: two manifest-less repositories under one parent that holds
      a manifest resolve to two different coordinates, and neither is the
      parent's.

### 1b. The corpus reaches the rows (design D2, D5, D6)

- [ ] 1.7 `schema/codiq.graphql`: `File` gains `corpus: String!` with a btree
      index. Update the `file.path` comment — "the corpus boundary is not
      modelled in M1" stops being true and the sentence that replaces it should
      say what is now modelled and what still is not (there is still no unique
      constraint; see 1.17).
- [ ] 1.8 Regenerate `schema/migrations/` with
      `gopgql generate --sdl schema/codiq.graphql --dir schema/migrations --name corpus`.
      Generated and committed, never hand-edited (`deploy/docker-compose.yml`'s
      `migrate` service comment).
- [ ] 1.9 `store/sqlc/query.sql`: `FileIDByPath` becomes a lookup on
      `(corpus, path)` and is renamed to say so; `InsertFile` and the advisory
      lock key both take the corpus. The lock keyed on `(corpus, path)` and not
      on `path` — otherwise two corpora's same-named files serialise on each
      other for no reason.
- [ ] 1.10 `facts.File` carries the corpus; `store.ReplaceFile` writes it;
      `store.resolveFile` looks up by the pair. Regenerate sqlc.
- [ ] 1.11 `artifact/codec.go` and `schema/proto/`: the corpus rides on the
      protobuf fact artifact, so a run that crashes after its map phase resumes
      with the corpus its artifacts were written under and not the one the
      resuming process was given. Regenerate with buf; adding a field is a
      compatible change, so `buf breaking` passes — if it does not, the field
      was added in a way that reuses a number and that is the bug.
- [ ] 1.12 `index.WorkflowVersion` bumped. A checkpointed batch from before this
      change carries artifacts with no corpus, and inheriting them would load
      rows the new identity cannot place.
- [ ] 1.13 `cmd/codiq`: `-corpus` flag, defaulting to `filepath.Base` of the
      resolved absolute repository root. `flag`, not cobra (design D5, and
      `SPEC.md` §12). The report prints the corpus.
- [ ] 1.14 `index.Result` carries the corpus so the report and the checkpoint
      agree.

### 1c. codiq's own spec

- [ ] 1.15 `SPEC.md` §4.4: the `file` table gains `corpus`; state that file
      identity is `(corpus, path)`.
- [ ] 1.16 `SPEC.md` §4.3: coordinate resolution is bounded by the repository,
      and a repository with no manifest is named by its corpus.
- [ ] 1.17 `SPEC.md` §16 or the SDL comment: a `(corpus, path)` unique
      constraint — which would let the loader drop its advisory lock for an
      `ON CONFLICT` — is now *possible* and is deliberately **not** taken here.
      Record it so it is not read as an oversight.
- [ ] 1.18 `deploy/docker-compose.yml`: the `codiq` service's long comment
      explaining why it indexes a fixture rather than codiq's own source is
      about the collision this milestone removes. Rewrite it rather than leaving
      a justification for a problem that no longer exists.

### Gate — M1

Real Postgres, real gopgql, via the existing godog + testcontainers harness.

- [ ] 1.19 `features/corpus.feature` + `test/integration/` scenario: index two
      fixture repositories that both contain a file at the same repo-relative
      path, each defining a same-named symbol in a same-named directory, then
      assert over MCP that (a) both files exist, (b) each has its own
      occurrences, and (c) **no derived edge joins the two corpora**. (c) is the
      assertion that would have failed before 1.1 and is the reason this
      milestone exists.
- [ ] 1.20 Scenario: a fixture repository with no manifest, placed under a
      directory that does have one, resolves to its own corpus-named coordinate.
- [ ] 1.21 Scenario: re-indexing one corpus leaves every other corpus's row
      counts unchanged and preserves the re-indexed corpus's file ids.
- [ ] 1.22 The existing M2–M9 integration suites still pass unchanged, which is
      what proves a single-repository index is unaffected.

## 2. M2 — index this workspace's projects  *(repo: `gaarutyunov/workspace`)*

### Precondition — disk (design D14)

- [ ] 2.1 **`df -h /System/Volumes/Data` reports ≥ 15 GiB free.** That path, not
      `df /` — on macOS `/` is the sealed system volume and its percentage
      lies. At the time this change was written the figure was **490 MiB, 100%
      used**, so this is a real gate and not a formality. `postgres:19beta2` and
      the `golang:1.25-alpine` layer both of codiq's Dockerfiles pull do not fit
      below it.
- [ ] 2.2 If any step hits `ENOSPC`: stop and report. Do not free space — no
      image prune, no module-cache clean, nothing outside a scratch directory.

### The run

- [ ] 2.3 `codiq/projects.yaml` in this repository: corpus name and path per
      project, the eight from Q2. `postgres-pglite` and `pglite` present but
      commented out, each with its reason (size; and for `postgres-pglite`, no
      manifest any resolver reads).
- [ ] 2.4 `codiq/index.py` — python3, matching
      `.claude/skills/loop-common/scripts/board-tick.py`, and not a shell script:
      the config is YAML and this machine has no Node, so python3 is the only
      runtime here that parses it without a dependency. It reads the file,
      brings codiq's compose stack up, then runs `docker compose run --rm -v
      <path>:/repo:ro codiq codiq -corpus <name> /repo` **once per project, in
      sequence** (design D7 — two concurrent indexers race in
      `link.RebuildAll`, measured as a foreign key violation). A missing path
      fails the run by name; a failing project is reported and the remainder
      continue.
- [ ] 2.5 Every value read from the config reaches `docker` as its own argv
      element — `subprocess.run([...])`, never `shell=True` and never an
      interpolated command string. A project path with a space or a quote in it
      is otherwise a command injection out of a file this repository treats as
      data.
- [ ] 2.6 The driver prints the per-project report codiq already emits — files
      walked, loaded, skipped with names, elapsed — plus the totals. This output
      is the comparison's index-cost input (5.5); do not measure it twice.
- [ ] 2.7 `codiq/README.md`: bring-up, index, tear-down, and the fact that a
      schema change means `down -v` and re-index rather than an in-place
      migration (design D6).

### Gate — M2

- [ ] 2.8 All eight projects indexed into one database in one run.
- [ ] 2.9 Assert over MCP that a repo-relative path present in more than one of
      the eight resolves to one file row **per corpus**. Identify such a path
      from the run first; if none of the eight share one, add a ninth project
      that does rather than declaring the gate vacuously passed.
- [ ] 2.10 Assert no derived edge crosses a corpus boundary — the M1 property, now
      on real repositories instead of fixtures.
- [ ] 2.11 Record per project: files present with a supported extension, files
      indexed, files skipped. A repository indexing far fewer files than it has
      is a finding for the comparison, not a failure of this gate.

## 3. M3 — settings, and connect

- [ ] 3.1 `.mcp.json`: a `codiq` server,
      `{"type":"http","url":"http://127.0.0.1:8080/mcp"}` — the shape
      `gopgql/examples/code-graph/.mcp.json` uses, against the endpoint codiq's
      compose `mcp` service publishes (`GOPGQL_ADDR :8080`, `GOPGQL_PATH`
      default `/mcp`).
- [ ] 3.2 `.claude/settings.json`: `mcp__codiq__*` in `permissions.allow`,
      beside `mcp__gortex__*`.
- [ ] 3.3 `AGENTS.md`: a short section — two code-graph servers are registered,
      what each is, and that `codiq` needs its stack up. Write the "which to
      reach for" sentence provisionally here; 5.8 rewrites it from the
      measurement.

### Gate — M3

- [ ] 3.4 From a session in this workspace with the stack up: `introspect`
      returns codiq's SDL, and `query` returns a named symbol from a named
      project — a real round trip, not a tool listing.
- [ ] 3.5 With the stack down, the failure is visible and diagnosable (design
      D9's stated cost). Record what it actually looks like in `AGENTS.md`.
- [ ] 3.6 A write attempted through the server is refused by the database, not
      merely absent from the tool list.

## 4. M4 — pre-registration  *(one commit, before any measurement)*

Design D11. The commit message states that it is the pre-registration.

- [ ] 4.1 `codiq/compare/corpus.yaml`: the eight repositories, each pinned to
      the exact commit indexed in M2.
- [ ] 4.2 `codiq/compare/questions.yaml`: 30 questions, six per category —
      (1) definition by name, (2) references to a symbol, (3) direct callers,
      (4) call path between two symbols, (5) a file's definitions,
      (6) cross-repository usage. Categories 1, 2, 3, 5, 6 are scored;
      category 4 is reported and ungated (4.6).
- [ ] 4.3 For every question, both operations, frozen: the gortex tool call with
      its arguments, and the codiq GraphQL document. Written before any is run.
- [ ] 4.4 `codiq/compare/key.yaml`: the expected result set per question, each
      element citing repository, path and symbol at the pinned commit,
      **authored from the source** and not from either system's output.
- [ ] 4.5 `codiq/compare/rule.md`: the decision rule, in advance — viable second
      source iff categories 1–3 each reach ≥0.90 recall **and** ≥0.90 precision,
      category 5 ≥0.90 recall, category 6 expressible. Otherwise "not yet",
      naming the failing category.
- [ ] 4.6 `codiq/compare/limits.md`: the known asymmetries, recorded before the
      run (design D13) — gopgql's default `MaxDepth` of 3 and the
      `*DepthExceededError` it raises (which is why category 4 is ungated);
      two MCP tools against roughly forty; gortex capabilities with no codiq
      analogue (dataflow, clones, blame/coverage/ownership, LSP, session memory)
      **listed and unscored**; codiq's arbitrary-SQL surface with no gortex
      analogue, likewise listed and unscored, demonstrated by one unscored
      question.

### Gate — M4

- [ ] 4.7 A reviewer can, from the pre-registration alone and with neither
      system running, restate every question, know exactly what each system will
      be asked, and know what result would mean "not yet".
- [ ] 4.8 `git log` shows this commit precedes every measurement commit. This is
      the whole mechanism; if the order is wrong the comparison is worthless and
      must be re-registered against fresh questions.

## 5. M5 — run the comparison, report it

- [ ] 5.1 gortex daemon started and the eight projects tracked
      (`gortex track projects/<repo>`), at the same pinned commits M2 indexed.
      Re-check 2.1's disk floor first: this is a second index of the same corpus.
- [ ] 5.2 Every frozen operation executed against both systems; raw results
      captured verbatim to `codiq/compare/results/`.
- [ ] 5.3 Scoring: expressible / recall / precision per question against
      `key.yaml`; latency as the median of three warm runs; request and response
      size per question (design D12).
- [ ] 5.4 A pre-registered query found to be **wrong** (not merely
      low-scoring) is amended in a separate commit carrying the reason, and both
      numbers are reported (design D11). No document is edited after seeing its
      score for any other cause.
- [ ] 5.5 Index cost from M2's report (2.6) plus on-disk bytes for each system's
      index.
- [ ] 5.6 `codiq/compare/report.md`: the full per-question table first,
      aggregates after, then the rule from 4.5 applied verbatim, then the
      unscored enumerations from 4.6.
- [ ] 5.7 If the outcome is "not yet": name the failing category and what would
      have to change. That is a complete result, not a reason to revisit 4.5.
- [ ] 5.8 `AGENTS.md`'s "which to reach for" sentence rewritten from the
      measurement, replacing 3.3's provisional wording.

### Gate — M5

- [ ] 5.9 Every one of the 30 pre-registered questions appears in the report,
      including inexpressible and zero-scoring ones.
- [ ] 5.10 Someone else, from `corpus.yaml`, `questions.yaml` and `key.yaml`
      alone, can rerun the comparison and reach the same numbers.
- [ ] 5.11 The conclusion follows from 4.5 as written, and no threshold in
      `rule.md` was modified after 4.8's commit. `git log rule.md` shows it.
