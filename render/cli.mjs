#!/usr/bin/env node
// Renders one preview (MP4) or one call sheet (PNG) from a JSON manifest.
//   node render/cli.mjs --kind preview|callsheet --manifest <abs.json> --out <abs path>
// Exit code 0 on success; on failure prints one line "render-error: <reason>" to stderr and exits 1.
// The bundle is built once and cached in render/.bundle (rebuilt when src/ changes).
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const MAX_MANIFEST_BYTES = 64 * 1024;

function arg(name) {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : undefined;
}

function fail(reason) {
  process.stderr.write(`render-error: ${reason}\n`);
  process.exit(1);
}

function srcHash() {
  const h = createHash("sha256");
  const walk = (d) => {
    for (const f of readdirSync(d).sort()) {
      const p = join(d, f);
      if (statSync(p).isDirectory()) walk(p);
      else h.update(f).update(readFileSync(p));
    }
  };
  walk(join(here, "src"));
  return h.digest("hex").slice(0, 16);
}

async function getBundle() {
  const cacheDir = join(here, ".bundle");
  const stamp = join(cacheDir, "stamp.txt");
  const want = srcHash();
  if (existsSync(stamp) && readFileSync(stamp, "utf8") === want && existsSync(join(cacheDir, "site", "index.html"))) {
    return join(cacheDir, "site");
  }
  mkdirSync(cacheDir, { recursive: true });
  const site = await bundle({ entryPoint: join(here, "src", "index.ts"), outDir: join(cacheDir, "site"), publicDir: join(here, "public") });
  writeFileSync(stamp, want);
  return site;
}

const kind = arg("kind");
const manifestPath = arg("manifest");
const out = arg("out");
if (!["preview", "callsheet"].includes(kind ?? "")) fail("--kind must be preview or callsheet");
if (!manifestPath || !out) fail("--manifest and --out are required");
if (statSync(manifestPath).size > MAX_MANIFEST_BYTES) fail("manifest too large");

let inputProps;
try {
  inputProps = JSON.parse(readFileSync(manifestPath, "utf8"));
} catch (e) {
  fail(`manifest is not valid JSON (${e.message})`);
}

try {
  const serveUrl = await getBundle();
  const id = kind === "preview" ? "Preview" : "CallSheet";
  // selectComposition and the render get the same props, so the schema validates exactly what is rendered.
  const composition = await selectComposition({ serveUrl, id, inputProps });
  mkdirSync(dirname(resolve(out)), { recursive: true });
  if (kind === "preview") {
    await renderMedia({ composition, serveUrl, codec: "h264", outputLocation: resolve(out), inputProps, crf: 20, pixelFormat: "yuv420p", concurrency: 4, timeoutInMilliseconds: 60000 });
  } else {
    await renderStill({ composition, serveUrl, output: resolve(out), inputProps, imageFormat: "png" });
  }
  process.stdout.write(`rendered ${kind} ${resolve(out)}\n`);
} catch (e) {
  fail(String(e?.message ?? e).split("\n")[0].slice(0, 300));
}
