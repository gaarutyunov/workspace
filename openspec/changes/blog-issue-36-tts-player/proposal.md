## Why

The issue asks for two things that pull in opposite directions:

> *"Add a small TTS model with transformers.js and a player to play the blogs.
> … highlight the words playing currently"*

**No in-browser TTS model reachable from JavaScript emits word timings.** That is
the finding that shapes this whole change, and it is worth stating before any
design follows from it:

| candidate | browser download | quality | word timing |
|---|---|---|---|
| **Kokoro-82M v1.0 ONNX** (`kokoro-js`) | **92 MB** q8 + 0.5 MB voice | best of the group | ✗ — but `stream()` yields one clip **per sentence**, so sentence boundaries are exact |
| `Xenova/speecht5_tts` + vocoder | **178 MB** q8 | noticeably worse, robotic | ✗ — autoregressive, no alignment output at all |
| Piper / vits-web | 30–60 MB per voice | below Kokoro | ✗ not exposed |
| `Kokoro-…-ONNX-timestamped` | 92 MB | identical | ✓ phoneme `durations` — but `kokoro-js` does not surface them; consuming it means driving `onnxruntime-web` directly **and** reimplementing Python `misaki` G2P in JS |
| **`speechSynthesis`** (built into the browser) | **0 MB** | OS-dependent | ✓ **real `boundary` events** with `charIndex`/`elapsedTime` |

So the highest-quality option has no timings, and the only option with real
timings is the one the issue did not ask for. The change resolves this rather
than picking a side: **sentence-accurate is the guaranteed floor, word-accurate is
best-effort**, and the player runs **two engines behind one interface** so the
blog is audible instantly and sounds good once the reader opts into the download.

The second finding is structural. Word highlighting needs a stable identity for
every word that is the *same object* in the text sent to the model and in the DOM
being highlighted. A runtime DOM walker and a build-time text artifact will drift
the first time a post contains a link, a code span or an em-dash. **This change
gives every prose word its identity once, at build time, in a rehype plugin** —
the DOM and the JSON artifact come out of the same pass, so they cannot disagree.

Third: `gaarutyunov/blog` has **no client-side application code today**. The only
`<script>` in the repo registers the ui-kit web components. It also has **no lint,
no typecheck and no tests in CI** — the PR-preview build succeeding is the only
gate. Landing the repo's first real browser application behind zero checks is not
acceptable, so this change adds `astro check` to CI as part of the deliverable.

## What Changes

- **A TTS player for the blog**, mounted site-wide, with two speech engines behind
  one `SpeechEngine` interface:
  - **browser voice** (`speechSynthesis`) — zero download, plays immediately, is
    what a first-time reader hears, and is the only engine on devices where the
    model will not fit;
  - **neural voice** (Kokoro-82M q8 via `kokoro-js`, WebGPU with WASM fallback,
    in a Web Worker) — **opt-in behind an explicit one-time ~93 MB download** with
    a progress UI, weights fetched from the Hugging Face CDN and cached by the
    browser. Never fetched on page load.
- **Build-time word indexing.** A rehype plugin wraps every spoken prose word in
  `<span class="tts-w" data-tts-w="N">` and emits the word list plus sentence
  ranges, which a static `/tts/<slug>.json` endpoint serves. Code blocks, inline
  code, SVG, `[aria-hidden]` and `[data-tts-skip]` are excluded from both.
- **Play from the post list** — a play control and an add-to-queue control per
  post on the index page, placed as siblings of `<ga-card>`, never inside it.
- **A queue** with add-to-queue / play-next and **reorder via up-down buttons**
  (keyboard- and touch-operable), with native drag as progressive enhancement.
- **Word highlighting** driven off `AudioContext.currentTime`: exact per sentence,
  interpolated across words within a sentence by character weight, or driven by
  real `boundary` events on the browser-voice engine where the platform fires them.
- **Persisted position.** Queue, current post, current word, engine, rate and voice
  live in `localStorage` under a key namespaced by `BASE_URL`. Reopening a post
  marks the last-played word and scrolls to it, clearing the sticky header and
  respecting `prefers-reduced-motion`.
- **`astro check` runs in CI** on every PR, and any pre-existing type errors it
  surfaces are fixed in the same PR.

## Impact

- **New**: `src/plugins/rehype-tts-words.mjs`, `src/pages/tts/[slug].json.ts`,
  `src/scripts/tts/*` (engine interface, both engine adapters, the Kokoro worker,
  queue store, highlighter, persistence), `src/components/TtsPlayer.astro`,
  `src/components/TtsPostControls.astro`.
- **Modified**: `astro.config.mjs` (rehype plugin), `src/layouts/BaseLayout.astro`
  (player mount + script entry), `src/layouts/PostLayout.astro` (TTS root hook),
  `src/pages/index.astro` (per-post controls), `src/styles/global.css` (highlight
  and player styles, all in `--ga-*` tokens), `package.json` (`kokoro-js`, `check`
  script), `.github/workflows/pr-preview.yml` (check step).
- **Runtime dependency on a third party**: the Hugging Face CDN. If it is down or
  the model repo is renamed, the neural voice fails and the player falls back to
  the browser voice. Weights are **never** vendored — GitHub blocks files >100 MB,
  and both workflows publish to the same `gh-pages` branch, so a vendored model
  would be copied into every open PR preview.
- **No content changes.** Post frontmatter is untouched.

## Non-goals

- Any language other than English.
- Downloadable/exportable audio files, or a podcast feed.
- Server-side or build-time audio pre-generation — the site is static SSG on
  GitHub Pages and stays that way.
- Offline-first guarantees. Browser cache eviction (notably Safari's ~7-day rule)
  can force a re-download; the player handles that gracefully but does not prevent it.
- The neural voice on phones. Kokoro's ~340 MB peak RAM makes mobile unreliable;
  mobile gets the browser voice and the spec says so rather than pretending.
- Voice cloning, per-post voice frontmatter, or a settings page beyond the
  player's own controls.

## Open decisions for the owner

1. **Two engines, or only the model?** The issue names transformers.js, and this
   change delivers it — but as the *opt-in quality tier*, not as the thing that
   plays when you press play. The alternative is model-only: nothing is audible
   until a 93 MB download completes, mobile is largely excluded, and word
   highlighting is interpolated everywhere with no real-timing path at all.
   **Recommendation: ship both.** The browser-voice adapter is small, and it is
   the only source of true word boundaries the platform offers.
2. **Astro `<ClientRouter />` for cross-page continuity.** Without view
   transitions, clicking a link stops playback and the reader resumes from the
   saved position. With `<ClientRouter />` + `transition:persist`, the queue plays
   straight through navigation. It is the right feature but it changes the whole
   site's navigation model and interacts with shadow-DOM web components.
   **Recommendation: attempt it, with "navigation stops playback and resumes from
   the saved position" as the accepted fallback if the ui-kit components misbehave**
   — verified on the PR preview, not assumed.
