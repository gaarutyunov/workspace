## 1. Feature file first

`features/*.feature` are hand-authored, canonical and single-source (SPEC §13.3).
They are written before the code and consumed by godog directly.

- [ ] 1.1 Rewrite the preamble of `features/author-and-publish.feature`: publishing
      is `epos push`; the `epos-registry` write path is still withdrawn and why.
- [ ] 1.2 Scenario: a packed skill is pushed and pulled back into a second store,
      landing on the digest `pack` printed.
- [ ] 1.3 Scenario: a pushed skill is pulled by plain `oras` — the conformance
      claim of SPEC §2.1 must survive the new publishing path.
- [ ] 1.4 Scenario: the published repository is `<namespace>/<skill-name>` and the
      remote tag is the version alone.
- [ ] 1.5 Scenario: pushing to a registry with authentication on is refused while
      logged out, and succeeds after `epos registry login`.
- [ ] 1.6 Scenario: a skill built from a Skillfile publishes with its provenance
      annotations intact.

## 2. Credential resolution — the shared client

Do this before `push`, because `push` is its first consumer and the sign path is
its second.

- [ ] 2.1 `internal/cli`: one constructor for the credential store —
      `--registry-config` path → `DOCKER_CONFIG` → Docker default plus native
      helpers → none (design **D8**). `credentials.NewStore` /
      `NewStoreFromDocker`, `AllowPlaintextPut` set.
- [ ] 2.2 `newRepository` in `pull.go` builds an `auth.Client` with
      `credentials.Credential(store)`; `newOCIRegistry` in `discover.go` gets the
      equivalent for `remote.Registry`.
- [ ] 2.3 **Compose, do not replace.** The `Epos-Download` transport becomes the
      auth client's inner `http.Client.Transport`
      (`&auth.Client{Client: &http.Client{Transport: headerTransport{…}}, …}`),
      so an authenticated pull is still counted as verified (SPEC §5.2). Assert
      this — it is the one thing a careless refactor breaks silently.
- [ ] 2.4 `push` gets the credential client **without** the `Epos-Download`
      transport: a publish is not a download (SPEC §5.1).
- [ ] 2.5 The 401 message reuses `discover.go`'s idiom —
      `errors.As(err, &*errcode.ErrorResponse)` and a switch on `StatusCode`,
      the way `unsupported()` does. Do not fold 403 into it: an unauthorised
      credential is a different problem from a missing one (design **D10**).
- [ ] 2.6 Test: resolution order, with a temp config for each source. No network.
- [ ] 2.7 Test: an authentication failure's message names the registry and
      contains neither the credential nor the header.
- [ ] 2.8 Test: a registry with no stored credential is still reached
      anonymously — credential resolution is per registry, and finding none is
      not an error. This is the compatibility case: `pull`, `verify`, `list` and
      `search` used to be unconditionally anonymous.

## 3. `epos registry login` / `logout`

- [ ] 3.1 `internal/cli/registry.go`: `registry` parent (help-only, `cobra.NoArgs`,
      matching `store`), with `login <host>` and `logout <host>`.
- [ ] 3.2 `-u/--username` (required), `--password-stdin`, `--registry-config`,
      `--plain-http`. **No `--password` flag** (design **D8**) — if a reviewer
      asks for one, the answer is in the design.
- [ ] 3.3 Fail with a message naming `--password-stdin` when stdin is neither a
      terminal nor carrying a secret; never prompt into a pipe and never store
      an empty secret.
- [ ] 3.4 Echo-off prompt via `golang.org/x/term` when stdin is a terminal and
      nothing was piped. Promote `golang.org/x/term` from indirect to direct.
- [ ] 3.5 `credentials.Login` verifies against the registry before storing, so a
      bad credential fails at login rather than at the next push.
- [ ] 3.6 `logout` is `credentials.Logout`; logging out of a host with no stored
      credential succeeds quietly rather than erroring.
- [ ] 3.7 Help text states in one sentence that without a native helper the
      credential is stored in a file, not encrypted.
- [ ] 3.8 Test (POSIX only, skipped on Windows): the written config is 0600 in a
      0700 directory.
- [ ] 3.9 Test: `--password-stdin` accepts a piped token; the secret reaches no
      `os.Args`.

## 4. `epos push`

- [ ] 4.1 `internal/cli/push.go`: `push <name>:<version> <destination>`,
      `cobra.ExactArgs(2)`, `SilenceUsage`, `RunE` calling a `runPush(ctx, out, …)`
      a test can drive directly the way `pull_test.go` drives `runPull`.
- [ ] 4.2 Destination parsing: strip a leading `oci://` if present (**D3**),
      append the skill name from the store tag (**D4**), parse through
      `registry.ParseReference` so a port survives.
- [ ] 4.3 Refuse a first operand that is a digest, with the shape of message
      `pull` uses; refuse one with no version, naming `epos store ls`.
- [ ] 4.4 Refuse a tag the store does not hold **before** any network request.
- [ ] 4.5 `store.Read` (shared lock) + `oras.Copy(ctx, st, "<name>:<version>",
      repo, "<version>", oras.DefaultCopyOptions)`. Nothing repacked, nothing
      re-derived (**D5**).
- [ ] 4.6 Print `<resolved-ref> <digest>` on one line (**D6**).
- [ ] 4.7 `--plain-http` and `--registry-config`, matching the flags `pull` and
      `login` carry.
- [ ] 4.8 Register `newPushCommand()` and `newRegistryCommand()` in
      `root.go`, and delete the package comment's "push is deliberately absent".
- [ ] 4.9 Table-driven unit tests over destination forms — with and without
      `oci://`, with and without a port, namespace ending in the skill's own name
      — asserting the resolved reference and remote tag. testify; `require` where
      the rest of the case depends on it.
- [ ] 4.10 Tests that need a store point `EPOS_HOME` at a `t.TempDir()`
      (`t.Setenv`). **Never set `HOME`** — it triggers permission prompts and
      `USERPROFILE` is the equivalent on Windows, where the unit matrix also runs.
- [ ] 4.11 **No `pusher` interface and no mock for the copy** (design **D10**).
      Unit tests cover parsing and refusal; the upload is covered against real
      zot in §5. An interface with one implementation would assert that
      `oras.Copy` was called.

## 5. Integration, against real zot

SPEC §13.2: registries are real. No fakes, no in-memory substitutes, no mocked
HTTP — including for the authentication scenarios.

- [ ] 5.1 Step definitions for 1.2–1.6 in `tests/integration`.
- [ ] 5.2 A zot container with htpasswd auth on, for 1.5. zot is chosen in §13.2
      partly for this; do not add a second registry image.
- [ ] 5.3 The auth scenario writes its credential into a temp registry config,
      never into the developer's `~/.docker/config.json`.
- [ ] 5.4 Assert the digest identity end to end: `pack` → `push` → `pull` and
      `pack` → `push` → plain `oras pull` both land on the digest `pack` printed.

## 6. The record

Every item here is a claim that is false once §4 lands.

- [ ] 6.1 `SPEC.md` §4.5 — retitle from "Write path — withdrawn" to name what is
      withdrawn (the `epos-registry` write path). Keep the GHSA reasoning, the
      rejected-alternatives table and the two-references consequence. Delete
      "`epos` has no `push` command"; add why the CLI's direct push is unaffected
      by the advisory (**D1**).
- [ ] 6.2 `SPEC.md` §6.1 — add `epos push` and `epos registry login/logout` to the
      command list; replace "There is no `epos push`".
- [ ] 6.3 `SPEC.md` §6.2 — the CLI still does not validate server-side or
      transform in transit; it *does* now hold the user's credentials, which line
      26 of the document already said while §6.2 denied it. Reconcile both.
- [ ] 6.4 `SPEC.md` §5.4 — keep "no publish counter" and its reasoning; drop the
      implication that no push command exists.
- [ ] 6.5 `SPEC.md` §12 row A2 and §15 rows 4 and 24 and the "Removed from scope"
      table.
- [ ] 6.6 `internal/docsgen/cli.go` — replace `publishing()`. It is prose, so the
      drift gate cannot catch it; this task is the only thing that will.
- [ ] 6.7 `go run ./internal/docsgen` and commit `cli.astro`. CI fails otherwise.
- [ ] 6.8 Grep the whole repo — `SPEC.md`, `README.md`, `features/`, `docs/` — for
      any surviving "no `epos push`" and fix what turns up.

## 7. Coordination with epos#42

- [ ] 7.1 Do **not** edit `docs/src/pages/quickstart.astro` here beyond what 6.8
      requires. #42 owns that page; #43 owns `push`'s own documentation.
- [ ] 7.2 If #42's spec is still open when this is implemented, raise on it that
      its `epos-quickstart` scenarios "Publishing is described as it actually
      works today" and "No invented commands" now need amending. If #42 has
      merged, amend them as part of this change.
