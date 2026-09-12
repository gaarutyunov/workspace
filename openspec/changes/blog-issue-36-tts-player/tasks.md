**One issue, one deliverable.** `gaarutyunov/blog#36` ships as a single pull
request. The stages below are an *ordering within that PR*, not milestones to be
split into separate issues or separate reviews.

**The ordering is not arbitrary.** Stage 1 mints word identity, and every later
stage consumes it (design D3). Stage 2 makes the blog audible with zero download,
so stages 3–6 can be built and verified without waiting on a 92 MB model. The
neural engine — the part the issue names — lands in stage 7, once there is a
player to plug it into.

**Definition of done for the PR:** every box below ticked, `astro check` green in
CI, and the verification in §8 performed on the deployed preview with its
measurements written into the PR description.

---

## 1. Word identity and the text resource

The foundation. Nothing else can be correct if this is wrong.

- [ ] Add `src/plugins/rehype-tts-words.mjs`: a rehype plugin that walks the post
      HAST, wraps each spoken word in `<span class="tts-w" data-tts-w="N">` inside
      block elements, and accumulates the word list and sentence ranges.
- [ ] Exclude `pre`, `code`, `svg`, `[aria-hidden="true"]` and `[data-tts-skip]`
      from both the spans and the word list.
- [ ] Place sentence boundaries on terminal punctuation **and** at block
      boundaries, so a heading is not glued to the paragraph after it.
- [ ] Never introduce a new direct child of `.prose` — `global.css` spaces the
      article with `.prose > * + *` and a new top-level child changes the rhythm.
- [ ] Expose the word list and sentence ranges through `remarkPluginFrontmatter`,
      and register the plugin in `astro.config.mjs`.
- [ ] Add `src/pages/tts/[slug].json.ts` — `getStaticPaths()` + `GET()`, modelled
      on `src/pages/rss.xml.js`, emitting `{ slug, title, words, sentences }`.
- [ ] Mirror `posts/[...slug].astro`'s draft handling (no filter) so the resource
      set matches the page set, and say so in a comment — `index.astro` and
      `rss.xml.js` filter drafts and `[...slug].astro` does not, which is a real
      inconsistency a reader will trip over.
- [ ] **Add a fixture post** exercising a code fence, an inline code span, a link,
      a blockquote, a list and an image, marked `draft: true`. The single existing
      post contains none of these, so without it the exclusion rules are untested
      (risk R9).

## 2. Player shell and the browser voice

The blog becomes audible here, with no download at all.

- [ ] Define the `SpeechEngine` interface in `src/scripts/tts/engine.ts`:
      `id`, `available`, `hasWordTiming`, `prepare()`, `speak()`, `cancel()`.
- [ ] Implement `src/scripts/tts/engine-browser.ts` over `speechSynthesis`.
      Use real `boundary` events for word timing where the platform fires them;
      where it does not, report `hasWordTiming: false` — never invent positions.
- [ ] Chunk long text: `speechSynthesis` drops silently past ~32 kB, and
      Chrome-on-Windows pauses after ~15 s. Speak one sentence per utterance.
- [ ] Add `src/components/TtsPlayer.astro` — the player bar — and mount it in
      `BaseLayout.astro` beside the existing ui-kit registration script.
- [ ] Wire play / pause / previous sentence / next sentence / rate, and show the
      current title and progress.
- [ ] Style it from `--ga-*` tokens only, reusing ui-kit components
      (`ga-button`, `ga-panel`, `ga-slider`, `ga-spinner`) where they fit.
      Pick the z-index deliberately against `ga-header` (`sticky`, `z-index: 50`).
- [ ] Accessibility to the standard the repo already holds: `aria-label` on every
      icon control, keyboard operability with a visible focus ring, an `aria-live`
      region for state changes, `prefers-reduced-motion` honoured.

## 3. List controls

- [ ] Add `src/components/TtsPostControls.astro` (play, add to queue, play next).
- [ ] Render it in `index.astro` as a **sibling of `<ga-card>`** inside the list
      item — never slotted into it. `ga-card` renders `<a class="card" href=…>`
      around its default slot, so a slotted button is a control inside a link and
      will navigate on click (risk R10).
- [ ] Mark the currently playing post in the list.
- [ ] Verify the card link still navigates when clicked away from the controls.

## 4. Queue

- [ ] `src/scripts/tts/queue.ts` — ordered slug list, current index, add / append /
      play-next / move up / move down / remove / clear, with change events.
- [ ] Auto-advance on sentence-stream completion, fetching the next post's text
      from `/tts/<slug>.json` via `import.meta.env.BASE_URL`. **A hard-coded
      absolute path breaks every PR preview** (risk: previews are served from
      `/pr-preview/pr-N/`).
- [ ] A queue view with per-row move-up / move-down / remove controls, all
      keyboard- and touch-operable. Drag only as an addition, if it is cheap.
- [ ] Handle the edges deliberately — the blog has **one** published post today,
      so empty, single-item, first-item and last-item are the common cases:
      disable controls that cannot act, rather than leaving them inert.
- [ ] Drop restored queue entries whose post no longer exists.
- [ ] A failed item reports and advances; it does not stall the queue.

## 5. Highlighting

- [ ] `src/scripts/tts/highlight.ts` — resolve a `(sentence, elapsed)` pair to a
      word index and paint `[data-tts-w]`.
- [ ] Drive the loop from `AudioContext.currentTime` inside `requestAnimationFrame`;
      for the browser voice, from `boundary` events or `elapsedTime`.
- [ ] Sentence highlight is exact and always on. Word highlight uses real timings
      when the engine has them, otherwise distributes the sentence's measured
      duration across its words by character weight (design D4).
- [ ] Highlight styles must not reflow: no padding, border or font-weight change
      that alters line breaking. Colours from tokens (e.g.
      `color-mix(in srgb, var(--ga-accent) …, transparent)`), legible on `#000`.
- [ ] Auto-scroll to keep the highlight in view, with `scroll-margin-top` clearing
      the sticky header, and `behavior: "auto"` under reduced motion — `global.css`
      sets `scroll-behavior: smooth` globally.
- [ ] Yield to manual scrolling; resume following when the reader returns.
- [ ] Attach and detach cleanly when the reader arrives at or leaves the playing
      post, without restarting playback.

## 6. Persistence and resume

- [ ] `src/scripts/tts/storage.ts` — one `localStorage` key,
      `blog:tts:v1:<BASE_URL>`, holding
      `{ queue, currentSlug, wordIndex, engineId, voiceId, rate, updatedAt }`.
- [ ] **Namespace by `BASE_URL`.** Previews share an origin with production; an
      un-namespaced key lets a preview overwrite the reader's real position.
- [ ] Save on sentence boundaries, on pause, and on `pagehide` / `visibilitychange`.
- [ ] On post load, if `currentSlug` matches, mark `[data-tts-w="<wordIndex>"]`
      with `.tts-w--resume` — visually distinct from the live highlight — and
      scroll to it under the same header/motion rules as §5.
- [ ] Restoring must not autoplay. Resuming continues from the saved word.
- [ ] Clear the resume mark once playback passes it.
- [ ] Malformed, versioned-out or clamped-out state is discarded silently; a
      browser that denies storage still gets a working player.

## 7. The neural voice

- [ ] Add `kokoro-js` to `package.json`.
- [ ] `src/scripts/tts/worker-kokoro.ts` — a Web Worker loading
      `onnx-community/Kokoro-82M-v1.0-ONNX` at `q8` with
      `device: "webgpu"`, falling back to `"wasm"`. **Dynamic `import()` only,
      never in a component frontmatter fence** — the module extends browser
      globals at load and would throw during SSR, exactly as `BaseLayout.astro`
      already documents for the ui-kit.
- [ ] Transfer PCM back as a transferable `Float32Array`.
- [ ] `src/scripts/tts/engine-neural.ts` — implement `SpeechEngine` over the
      worker, using `stream()` so audio starts before the whole post is
      synthesised, and taking each sentence's true duration from
      `audio.length / sampling_rate`.
- [ ] `src/scripts/tts/audio.ts` — schedule each sentence's `AudioBuffer` on one
      shared `AudioContext` timeline (`start(nextTime); nextTime += duration`).
      Not `<audio>`: a Blob URL per sentence gaps audibly and `timeupdate` at
      ~4 Hz cannot drive word highlighting.
- [ ] Opt-in flow: state the approximate download size **before** starting it,
      show progress, keep the browser voice usable throughout, remember the
      choice. Nothing is fetched on page load.
- [ ] Surface failures — host unreachable, backend unavailable, cache evicted —
      and fall back to the browser voice rather than dying.
- [ ] Never commit weights. Both workflows publish to the same `gh-pages` branch,
      so a vendored model would be duplicated into every open preview.
- [ ] If `npm ci` proves troublesome (`node_modules` is absent and the ui-kit needs
      a `read:packages` token), the escape hatch is a CDN ESM import inside the
      worker — record which path was taken and why.

## 8. Cross-page continuity — attempt, then decide

- [ ] Add `<ClientRouter />` and mark the player `transition:persist` so playback
      survives in-site navigation.
- [ ] Verify on the preview that `ga-header` and `ga-card` still behave — they are
      shadow-DOM custom elements and view transitions change the navigation model.
- [ ] **If they misbehave, remove it.** The accepted fallback is: navigation stops
      playback, and the saved position resumes it. Record which outcome held and
      why — do not leave this to a later reader to rediscover (design D10).

## 9. CI and verification

- [ ] Add `"check": "astro check"` to `package.json` and a step to
      `.github/workflows/pr-preview.yml`, running **before** the build.
- [ ] Fix — do not suppress — every error it surfaces in pre-existing files.
      There are 28 tracked files; `rss.xml.js` is plain JS and `tsconfig.json`
      extends `astro/tsconfigs/strict`.
- [ ] Verify on the **deployed preview** with headless Chrome. There is no Node on
      the development machine, so nothing here can be proven locally (risk R5):
  - [ ] play from the list without navigating; play from a post page
  - [ ] add to queue, play next, reorder up/down, remove, clear
  - [ ] word and sentence highlight track the audio on both engines
  - [ ] reload mid-post: the word is marked, the view moves to it, resume continues
  - [ ] preview state does not touch production state (check the storage key)
  - [ ] keyboard-only operation of every control; reduced-motion behaviour
  - [ ] the fixture post's code block, inline code and image are not read aloud
- [ ] **Measure and record in the PR description:**
  - [ ] neural synthesis throughput on WebGPU **and** on single-threaded WASM —
        this decides whether the neural engine is offered without a GPU backend
        (risk R2), and the published figures assume WebGPU
  - [ ] the gzipped page-size delta from per-word spans (risk R7)
  - [ ] which engines and browsers were actually exercised
- [ ] Update the PR body with the outcomes of §8 and the measurements above.
