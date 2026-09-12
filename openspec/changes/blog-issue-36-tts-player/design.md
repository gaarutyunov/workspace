# Design

Fourteen decisions. Each records what was rejected, because on this feature the
rejected options are where the cost lives.

---

## D1 — The neural engine is Kokoro-82M q8 via `kokoro-js`, not SpeechT5

**Decision.** `onnx-community/Kokoro-82M-v1.0-ONNX`, `model_quantized` (q8,
92.4 MB) plus one voice `.bin` (~522 kB, fetched per voice — not the whole 54 MB
voice folder). Apache-2.0. `device: "webgpu"` with automatic fallback to
`"wasm"`.

**Why not SpeechT5**, which is the model most transformers.js TTS examples use:
q8 it is encoder 88.4 + decoder 71.1 + postnet/vocoder 18.3 ≈ **178 MB** — nearly
double Kokoro — for audio that is audibly worse (robotic, unstable prosody), and
it is autoregressive so it is also slower. It has no alignment output of any kind.
There is no axis on which it wins.

**Why not Piper**, at 30–60 MB the smallest real option: quality sits clearly
below Kokoro and its web wrappers expose no durations either, so the size saving
buys nothing that Kokoro's sentence streaming does not already give us.

**Why not `Kokoro-82M-v1.0-ONNX-timestamped`**, which genuinely emits phoneme
`durations` in its ONNX graph: `kokoro-js` does not surface that output, so using
it means driving `onnxruntime-web` directly *and* reimplementing the upstream
`misaki` G2P phonemizer — which is Python — in JavaScript. That is a large,
poorly-trodden path, and the repo's own discussion thread reports significant
timing deviation against a real forced aligner anyway. Revisit only if `kokoro-js`
starts exposing durations upstream.

**On "transformers.js" in the issue title.** `kokoro-js` is built on
`@huggingface/transformers` — this is transformers.js, packaged with the
tokenizer and phonemizer the model needs.

## D2 — Two engines behind one interface; the browser voice is what plays first

**Decision.** A single `SpeechEngine` interface with two implementations:

```ts
interface SpeechEngine {
  readonly id: "browser" | "neural";
  readonly available: boolean;
  prepare(onProgress?: (p: LoadProgress) => void): Promise<void>;
  speak(sentence: Sentence, rate: number): AsyncIterable<SpeechChunk>;
  cancel(): void;
}
```

The **browser voice** (`speechSynthesis`) is the default and needs no preparation.
The **neural voice** is selectable in the player and calls `prepare()`, which
shows a download progress UI and only then becomes the active engine. The choice
persists (D12).

**Why.** 92 MB is not a thing to spend a reader's bandwidth on before they have
heard a single word — and the download is one-way: the reader cannot evaluate
whether they want the better voice until after paying for it. Starting on the
browser voice makes "play" instant, makes the feature work on phones (where
Kokoro's ~340 MB peak RAM is unreliable), and gives a defined behaviour when
WebGPU is absent and single-threaded WASM turns out too slow to sustain
real-time — a risk that is **unmeasured** (see D4/R2).

It also buys the one thing no model offers: `speechSynthesis` fires real
`boundary` events carrying `charIndex` and `elapsedTime`, which is *actual* word
timing rather than interpolation.

**Rejected: model-only.** Simpler, matches the issue literally, and produces a
blog where pressing play does nothing for a minute on first use, nothing at all
on an iPhone, and where every highlight is an estimate.

**Rejected: browser-voice-only.** Cheapest by far, but it declines the issue's
actual request and its quality is entirely at the mercy of the reader's OS —
excellent on macOS, poor on many Linux and older Android configurations.

## D3 — Word identity is minted once, at build time, by a rehype plugin

**Decision.** `src/plugins/rehype-tts-words.mjs` runs in Astro's markdown
pipeline. It walks the post's HAST, and inside every spoken block element it
replaces text nodes with a sequence of
`<span class="tts-w" data-tts-w="N">word</span>` elements, `N` monotonically
increasing across the whole post. In the same pass it accumulates the word list
and the sentence ranges, and writes them to `remarkPluginFrontmatter` so
`render(post)` exposes them to the `/tts/<slug>.json` endpoint (D5).

**Why this is the load-bearing decision.** The alternative — a runtime
`TreeWalker` over `.prose` on the post page, plus a separately generated text
artifact for list-page playback — has two tokenizers that must agree forever.
They will not: Markdown links, inline code, smart quotes, footnotes and
`astro-icon` SVG all get tokenized differently by a HAST walker and by a
markdown-string splitter, and the failure mode is a highlight that silently drifts
one word further off with every paragraph. Minting identity once means the JSON
the model reads and the spans the highlighter paints are **the same objects by
construction**.

**Cost, stated plainly.** ~1,100 words × ~30 bytes of span markup ≈ 33 kB of extra
HTML per post before gzip (gzip handles this class of repetition well; measure on
the preview and record the number). It also puts spans in the DOM for readers who
never press play. Accepted: the alternative is a feature that does not work.

**Constraint from `global.css`.** `.prose` spaces its children with
`.prose > * + *`. The plugin therefore wraps words **inside** block elements and
never introduces a new top-level child of `.prose`, so sibling counts and vertical
rhythm are untouched.

## D4 — Timing: sentences are measured, words are interpolated

**Decision.** Two levels, and the spec commits to them separately:

1. **Sentence level is exact.** `kokoro-js`'s `stream()` splits on sentences by
   default and yields `{ text, phonemes, audio }` per chunk; the clip's true
   duration is `audio.length / audio.sampling_rate`. Scheduling those clips on a
   shared `AudioContext` timeline gives an exact start time for every sentence.
2. **Word level within a sentence is interpolated**, distributing the measured
   sentence duration across its words weighted by character count.

On the **browser voice**, real `boundary` events drive word highlighting directly
when the platform fires them; when they do not fire (Safari, several Chrome
voices — `boundary` is not Baseline), the engine reports word timing as
unavailable and the player degrades to sentence-level highlighting.

**Why interpolation is good enough.** Error is bounded *within one sentence* and
resets at every sentence boundary, so it cannot accumulate over a post. It
degrades on long sentences, heavy punctuation pauses, numbers and acronyms.

**What the spec promises**: sentence-accurate highlighting, always. Word-accurate
highlighting, best-effort. Anyone reading the requirements should be able to tell
which is which without reading this file.

## D5 — `/tts/<slug>.json` is a static endpoint, modelled on `rss.xml.js`

**Decision.** `src/pages/tts/[slug].json.ts` with `getStaticPaths()` + `GET()`,
prerendered at build like every other route, returning:

```jsonc
{ "slug": "...", "title": "...",
  "words": ["Loop", "engineering", "is", ...],
  "sentences": [{ "start": 0, "end": 12, "text": "..." }, ...] }
```

`src/pages/rss.xml.js` is the in-repo precedent for a generated non-HTML route.
Its one trap: it uses `context.site` (the production origin), while pages use
`import.meta.env.BASE_URL`. **The client fetches this endpoint via
`import.meta.env.BASE_URL`**, or every PR preview under `/pr-preview/pr-N/` 404s.

**Why an endpoint at all**, when the post page already has the words in its DOM:
playing from the *list* page, and playing the *next* item in the queue, both need
a post's text without navigating to it. The post page itself reads its words from
the DOM — same identity space, no fetch.

**One deliberate choice to make and record:** `index.astro` and `rss.xml.js`
filter `draft`, but `posts/[...slug].astro` does **not** — drafts get pages today.
The endpoint mirrors `[...slug].astro` (no filter) so the artifact set matches the
page set exactly; the *list* controls only appear for non-draft posts, because the
list itself is filtered.

## D6 — Playback is Web Audio, not `<audio>`

**Decision.** One `AudioContext`; each sentence's PCM becomes an `AudioBuffer`
scheduled with `source.start(nextTime); nextTime += buffer.duration`. Highlight
position is read from `audioContext.currentTime` inside `requestAnimationFrame`.

**Why.** The model hands back raw `Float32Array` PCM, which is exactly what Web
Audio takes. `MediaSource` does not accept raw PCM at all. A Blob-URL `<audio>`
element per sentence produces audible gaps at every sentence boundary, and its
`timeupdate` fires at roughly 4 Hz — far too coarse to drive word highlighting,
where `AudioContext.currentTime` is sub-millisecond.

**Media Session API** (OS-level media keys and lock-screen controls) is a
progressive enhancement only: it typically requires a real media element to be
playing before the OS shows the widget, and it is not Baseline. Wire it if it
works on the preview; do not build the player around it.

## D7 — Synthesis runs in a Web Worker. Not optional

**Decision.** Kokoro runs in a dedicated Worker; PCM comes back as a transferable
`Float32Array`.

**Why it is not optional.** GitHub Pages cannot set COOP/COEP response headers, so
`crossOriginIsolated` is `false`, `SharedArrayBuffer` is unavailable, and ONNX
Runtime Web silently falls back to **single-threaded** WASM — commonly ~3–4×
slower than the multithreaded path. On the main thread, per-sentence synthesis
would block for hundreds of milliseconds to seconds, visibly janking the UI and
the highlight loop. WebGPU, where present, does not require COOP/COEP and stays
the fast path.

## D8 — Weights load from the Hugging Face CDN at runtime, and are never vendored

**Decision.** `kokoro-js` fetches from the HF CDN (permissive CORS, no proxy of
ours needed) and transformers.js caches into the browser **Cache API**
automatically. Self-host the ONNX Runtime `.wasm` binaries under `public/` only
if a strict CSP is ever added — and if so, prefix their path with
`import.meta.env.BASE_URL`.

**Why never vendor.** GitHub rejects pushes of files over 100 MB. Worse, both
`deploy.yml` and `pr-preview.yml` publish to the same `gh-pages` branch, so a
vendored model would be copied into **every open PR preview** under
`pr-preview/pr-N/`, against a ~1 GB Pages limit.

**Accepted risk (R4).** The HF CDN is a third-party runtime dependency. Outage or
repo rename ⇒ the neural engine fails; the player says so and falls back to the
browser voice.

## D9 — Libraries are imported dynamically, inside client scripts only

**Decision.** `kokoro-js` is added to `package.json`, and imported with a **dynamic
`import()` at first use of the neural engine**, inside a bundled Astro `<script>`
(or the Worker), never in a component's frontmatter fence.

**Why.** `BaseLayout.astro` already documents the rule for this repo: importing
the ui-kit in frontmatter "would throw because it extends HTMLElement at module
load." `onnxruntime-web` has the same property. Dynamic import additionally keeps
the WASM glue out of the initial bundle for readers who never press play.

**Note for implementation:** `node_modules` is not present in the worktree and
there is no Node on the dev machine, so `npm install` of `kokoro-js` cannot be
verified locally. CI is the proving ground (D14). If `npm ci` proves problematic,
a CDN ESM import (`https://cdn.jsdelivr.net/npm/kokoro-js@…/+esm`) inside the
Worker is the escape hatch — it needs no build-time npm step at all.

## D10 — Cross-page continuity: attempt `<ClientRouter />`, with a stated fallback

**Decision.** Queue playback is **page-independent** — the player streams the next
item's text from its JSON artifact and plays it without navigating anywhere. On
top of that, add Astro's `<ClientRouter />` and mark the player bar
`transition:persist` so playback also survives the reader clicking a link.

**The fallback is part of the decision, not a contingency.** View transitions
change the whole site's navigation model and interact with shadow-DOM web
components (`ga-header`, `ga-card`). If they misbehave on the preview, drop
`<ClientRouter />`: navigation then stops playback, and the saved position (D12)
resumes it. Verify on the deployed preview; do not assume either outcome.

## D11 — Queue reorder is up-down buttons; drag is an enhancement

**Decision.** Every queue row carries "move up" / "move down" buttons with
`aria-label`s. Native HTML5 drag-and-drop is layered on top if it is cheap.

**Why.** Buttons are keyboard-operable, work on touch without a long-press
gesture, and are announced by screen readers — and this repo already takes
accessibility seriously (`aria-label` on every icon link, `aria-current`,
`<time datetime>`, `rel="noopener noreferrer"`, semantic landmarks throughout).
Drag-only reorder would be the least accessible control in the codebase.

## D12 — Persistence is `localStorage`, namespaced by `BASE_URL`

**Decision.** One key, `blog:tts:v1:<BASE_URL>`, holding
`{ queue: string[], currentSlug, wordIndex, engineId, rate, voiceId, updatedAt }`.
Written on pause, on sentence boundaries, and on `visibilitychange`/`pagehide`.

**Why namespaced.** PR previews are served from the *same origin* as production
(`blog.garutyunov.com/pr-preview/pr-N/`), so an un-namespaced key would let
preview state overwrite the reader's real position — and vice versa.

**Why not IndexedDB.** The payload is a few hundred bytes and wants to be written
synchronously during `pagehide`. IndexedDB earns its place only if generated audio
is ever cached across sessions, which is a non-goal.

## D13 — Resume marks the word and scrolls to it, carefully

**Decision.** On post-page load, if the saved `currentSlug` matches, apply
`.tts-w--resume` to `[data-tts-w="<wordIndex>"]` and scroll it into view.

**Two things in `global.css` make this non-trivial**, and both are requirements
rather than polish: `ga-header` is `position: sticky; top: 0; z-index: 50`, so the
target needs `scroll-margin-top` clearing it or the marked word lands *under* the
header; and `html { scroll-behavior: smooth }` is set globally, so the jump
animates — use `behavior: "auto"` under `prefers-reduced-motion: reduce`.

## D14 — `astro check` runs in CI, in this PR

**Decision.** Add `"check": "astro check"` to `package.json` and a step running it
to `pr-preview.yml`, before the build.

**Why this belongs to this change and not a follow-up.** The repo has **no lint,
no typecheck and no tests** — a successful build is the entire gate — and this
change lands the repo's first substantial client-side application, in strict-mode
TypeScript (`tsconfig.json` extends `astro/tsconfigs/strict`). A type error or a
runtime exception in the player would deploy green today. `astro check` will also
start checking the pre-existing files, including the plain-JS `rss.xml.js`; there
are 28 tracked files, so **any errors it surfaces are fixed in this PR** rather
than suppressed or deferred.

---

## Risks

| # | risk | mitigation |
|---|---|---|
| R1 | 92 MB download on a personal blog | Never automatic. Explicit opt-in, progress UI, browser voice plays meanwhile (D2). |
| R2 | **Single-threaded WASM may not sustain real-time.** The published throughput figures are WebGPU-path; the no-COOP/COEP WASM number is unmeasured. | Measure on the PR preview across WebGPU and WASM before merge, and record the number. If WASM cannot keep up, the neural engine is offered only where WebGPU is present; the browser voice covers the rest (D2). |
| R3 | Word highlight is interpolated, not measured | Sentence-level accuracy is the contract; word-level is best-effort and the spec says so (D4). |
| R4 | HF CDN is a third-party runtime dependency | Detected and surfaced in the UI; falls back to the browser voice (D8). |
| R5 | **Nothing can be verified locally** — no Node, no `node_modules`, and `npm ci` needs a `read:packages` token for the ui-kit from GitHub Packages | CI + the deployed PR preview, driven with headless Chrome, is the verification path (D14, tasks §7). |
| R6 | Cache eviction (Safari ~7-day) silently re-downloads 92 MB | Re-download is shown with the same progress UI, not silent; the browser voice remains available throughout. |
| R7 | Per-word spans bloat every post's HTML (~33 kB pre-gzip) | Measure the real gzipped delta on the preview and record it; the design has no drift-free alternative (D3). |
| R8 | `<ClientRouter />` may break the ui-kit web components | Fallback is defined and acceptable up front (D10). |
| R9 | Future posts will contain code fences (Shiki renders deep `<span>` soup) and inline SVG | The rehype plugin excludes `pre`, `code`, `svg`, `[aria-hidden="true"]` and `[data-tts-skip]` from both the spans and the JSON. Today's single post has none of these, so this must be tested against a fixture post that does. |
| R10 | A play `<button>` inside `<ga-card href>` nests a control in a link and navigates on click | Controls are rendered as **siblings** of `<ga-card>` inside the list item, never slotted into it (spec `blog-tts-player`). |
