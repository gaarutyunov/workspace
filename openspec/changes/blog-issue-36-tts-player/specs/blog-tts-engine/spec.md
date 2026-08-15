## ADDED Requirements

**Two engines behind one interface (design D2). The blog is audible with no
download; the neural voice is what a reader opts into. The interface exists so
the player, the queue and the highlighter never branch on which engine is active.**

### Requirement: Speech is produced through a single engine interface

All speech synthesis SHALL be reached through one interface, so that engines are
interchangeable at runtime.

#### Scenario: The player does not know which engine is speaking
- **WHEN** the player, queue or highlighter requests speech
- **THEN** it uses the same interface regardless of the active engine

#### Scenario: An engine reports whether it can run here
- **WHEN** the player enumerates engines
- **THEN** each engine reports whether it is available on this device and browser,
  and an unavailable engine is not offered

#### Scenario: An engine declares whether it can time words
- **WHEN** an engine is activated
- **THEN** it declares whether it can supply word-level timing, so the
  highlighter can choose word or sentence granularity without guessing

#### Scenario: Speech is delivered per sentence
- **WHEN** an engine speaks
- **THEN** it emits results one sentence at a time, so playback can begin before
  the whole post has been synthesised

#### Scenario: Speech can be cancelled promptly
- **WHEN** the reader pauses, skips, or changes engine mid-sentence
- **THEN** synthesis and playback stop without waiting for the remaining text

### Requirement: The browser voice is the default engine and needs no download

An engine backed by the browser's built-in speech synthesis SHALL be the initial
engine.

#### Scenario: Playback starts immediately on first visit
- **WHEN** a reader presses play for the first time, having chosen nothing
- **THEN** speech begins with no model download and no preparation step

#### Scenario: Real word boundaries are used when the platform emits them
- **WHEN** the browser emits word-boundary events during an utterance
- **THEN** the engine reports word-level timing from those events rather than
  estimating it

#### Scenario: Missing boundary events are reported, not faked
- **WHEN** the browser does not emit word-boundary events
- **THEN** the engine declares word-level timing unavailable, and highlighting
  degrades to sentence level rather than producing invented word positions

#### Scenario: The engine is unavailable where the API is absent
- **WHEN** the browser provides no speech synthesis
- **THEN** this engine reports itself unavailable

### Requirement: The neural voice is opt-in and never downloads unprompted

The neural engine SHALL require an explicit reader action before fetching model
weights.

#### Scenario: No weights are fetched on page load
- **WHEN** any page of the blog loads
- **THEN** no model weights are requested

#### Scenario: The reader is told the cost before paying it
- **WHEN** the reader is offered the neural voice
- **THEN** the approximate one-time download size is stated before the download starts

#### Scenario: Download progress is visible
- **WHEN** model weights are downloading
- **THEN** progress is shown, and the reader can continue listening on the browser
  voice while it completes

#### Scenario: The choice is remembered
- **WHEN** the reader has chosen the neural voice and returns later
- **THEN** that choice is remembered, and cached weights are reused without a
  second download

#### Scenario: A repeat download is announced, not silent
- **WHEN** cached weights have been evicted by the browser
- **THEN** the re-download is surfaced with the same progress treatment rather
  than appearing as an unexplained delay

### Requirement: The neural engine degrades instead of failing

The neural engine SHALL treat unavailability as a defined state.

#### Scenario: Model weights cannot be fetched
- **WHEN** the model host is unreachable or returns an error
- **THEN** the failure is surfaced to the reader in the player, and the browser
  voice remains usable

#### Scenario: Hardware acceleration is absent
- **WHEN** the browser provides no GPU compute backend
- **THEN** the engine falls back to the CPU backend rather than reporting failure

#### Scenario: The CPU backend cannot keep up
- **WHEN** measurement shows synthesis on the CPU backend cannot sustain playback
  on the target hardware
- **THEN** the neural engine is not offered on devices without the GPU backend,
  and the measured figures are recorded in the change rather than assumed

#### Scenario: Cancellation does not leak work
- **WHEN** playback is cancelled while synthesis is in flight
- **THEN** pending synthesis is abandoned and its results are discarded

### Requirement: Neural synthesis does not run on the main thread

Model inference SHALL run off the main thread.

#### Scenario: The interface stays responsive during synthesis
- **WHEN** the neural engine is synthesising
- **THEN** scrolling, the player controls and the highlight animation remain
  responsive, because the host cannot serve the headers that would enable
  multi-threaded CPU inference and a main-thread run would block for seconds

#### Scenario: Audio is handed back without copying
- **WHEN** synthesised audio is returned from the worker
- **THEN** it is transferred rather than structurally cloned

### Requirement: Model weights are loaded at runtime and never committed

Model weights SHALL be fetched from their upstream host at runtime.

#### Scenario: Weights are not in the repository
- **WHEN** the repository is inspected
- **THEN** it contains no model weights, because the publishing branch is shared
  by production and every open preview, which would multiply their size

#### Scenario: Weights are cached by the browser between visits
- **WHEN** a reader who has already downloaded the model returns
- **THEN** the model loads from the browser cache without a network fetch of the
  weights

#### Scenario: Any self-hosted runtime asset resolves under the base path
- **WHEN** a runtime asset is served from the site itself rather than a CDN
- **THEN** its URL is built from the site's configured base path so that preview
  deployments resolve it
