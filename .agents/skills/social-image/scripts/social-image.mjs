#!/usr/bin/env node
/* Deterministic social-image generator — NO AI.
 *
 * Renders HTML with headless Chromium (Playwright) and screenshots it at the
 * 1200x630 Open Graph size. Two modes:
 *
 *   A) --url <landing> [--selector <css>]   screenshot a live landing's hero
 *   B) --hero --title --tagline --icon <p>  render a throwaway ui-kit hero
 *
 * Output: --out (default public/og-image.png), a 1200x630 PNG.
 *
 * Chromium is installed on demand via `npx playwright install chromium`.
 */
import { spawnSync } from "node:child_process";
import { mkdtemp, writeFile, readFile, copyFile, rm, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const OG_WIDTH = 1200;
const OG_HEIGHT = 630;
const DEFAULT_SELECTORS = ["[data-hero]", ".hero", "header", "main > header", "main"];
const here = dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith("--")) {
        args[key] = true;
      } else {
        args[key] = next;
        i++;
      }
    }
  }
  return args;
}

function fail(msg) {
  console.error(`social-image: ${msg}`);
  process.exit(1);
}

/** Import Playwright, resolving it from the project's cwd first.
 *  The script lives in the skills repo, so a bare `import("playwright")`
 *  resolves against the script's location — not the pet project that installed
 *  playwright. Resolve from cwd's node_modules so `npm i -D playwright` in the
 *  project works. */
async function importPlaywright() {
  try {
    return await import("playwright");
  } catch {
    /* fall through to cwd resolution */
  }
  try {
    const req = createRequire(join(process.cwd(), "package.json"));
    return await import(pathToFileURL(req.resolve("playwright")).href);
  } catch {
    return null;
  }
}

/** Lazily import Playwright, installing Chromium on first use if needed. */
async function loadChromium() {
  const pw = await importPlaywright();
  if (!pw) {
    fail(
      "Playwright is not installed. Run `npm i -D playwright` in the project " +
        "(or `npx playwright`), then re-run. This skill uses no AI — just a headless browser.",
    );
  }
  // When resolved from a file path, CJS→ESM interop may nest exports under .default.
  const chromium = pw.chromium ?? pw.default?.chromium;
  if (!chromium) fail("could not load Playwright's chromium export.");
  try {
    const browser = await chromium.launch();
    return { chromium, browser };
  } catch {
    // Browser binary missing — install it once, then retry.
    console.error("social-image: installing Chromium (first run)…");
    const r = spawnSync("npx", ["playwright", "install", "chromium"], {
      stdio: "inherit",
    });
    if (r.status !== 0) fail("`npx playwright install chromium` failed.");
    const browser = await chromium.launch();
    return { chromium, browser };
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function renderHeroToTempDir({ title, tagline, iconPath }) {
  const templatePath = join(here, "hero-template.html");
  let html = await readFile(templatePath, "utf8");

  // Validate the icon before creating the temp dir, and throw (not fail/exit)
  // so main()'s finally block still runs its browser/temp cleanup.
  let iconAbs = null;
  if (iconPath) {
    iconAbs = resolve(process.cwd(), iconPath);
    if (!existsSync(iconAbs)) throw new Error(`--icon not found: ${iconPath}`);
  }

  const dir = await mkdtemp(join(tmpdir(), "social-image-hero-"));
  // Copy the icon next to the HTML so the page can reference it relatively.
  let iconRef = "";
  if (iconAbs) {
    await copyFile(iconAbs, join(dir, "icon.png"));
    iconRef = "./icon.png";
  }

  html = html
    .replaceAll("{{TITLE}}", escapeHtml(title ?? ""))
    .replaceAll("{{TAGLINE}}", escapeHtml(tagline ?? ""))
    .replaceAll("{{ICON}}", iconRef);

  const htmlPath = join(dir, "hero.html");
  await writeFile(htmlPath, html, "utf8");
  return { dir, url: pathToFileURL(htmlPath).toString() };
}

async function capture(page, { selector }) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});

  // The context viewport is fixed at OG_WIDTH x OG_HEIGHT, so a plain viewport
  // screenshot is exactly 1200x630 — no clip (which can go out of bounds).
  if (selector === "__viewport__") {
    return page.screenshot({ type: "png" });
  }

  const candidates = selector ? [selector] : DEFAULT_SELECTORS;
  for (const sel of candidates) {
    const el = await page.$(sel);
    if (!el) continue;
    // Scroll the hero to the viewport's top-left, then capture the fixed
    // viewport. Aligning by scroll (not a page-coordinate clip) keeps the frame
    // in-bounds even when the hero sits below the fold.
    await el.evaluate((e) => e.scrollIntoView({ block: "start", inline: "start" }));
    return page.screenshot({ type: "png" });
  }
  throw new Error(
    `no hero element matched (${(selector ? [selector] : DEFAULT_SELECTORS).join(
      ", ",
    )}). Pass --selector to point at the hero.`,
  );
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const out = resolve(process.cwd(), args.out || "public/og-image.png");

  const heroMode = !!args.hero;
  if (!heroMode && !args.url) {
    fail("provide --url <landing> [--selector <css>], or --hero --title --tagline --icon <path>.");
  }

  const { browser } = await loadChromium();
  let tempDir = null;
  try {
    const context = await browser.newContext({
      viewport: { width: OG_WIDTH, height: OG_HEIGHT },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();

    let selector;
    if (heroMode) {
      const rendered = await renderHeroToTempDir({
        title: args.title,
        tagline: args.tagline,
        iconPath: args.icon,
      });
      tempDir = rendered.dir;
      await page.goto(rendered.url, { waitUntil: "load" });
      selector = "__viewport__";
    } else {
      await page.goto(args.url, { waitUntil: "load" });
      selector = typeof args.selector === "string" ? args.selector : undefined;
    }

    const png = await capture(page, { selector });
    await mkdir(dirname(out), { recursive: true });
    await writeFile(out, png);
    console.log(`social-image: wrote ${out} (${OG_WIDTH}x${OG_HEIGHT})`);
  } finally {
    await browser.close();
    if (tempDir) await rm(tempDir, { recursive: true, force: true });
  }
}

main().catch((e) => fail(e?.message || String(e)));
