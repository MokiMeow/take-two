#!/usr/bin/env node
// Renders one preview (MP4) or one call sheet (PNG) from a JSON manifest.
//   node render/cli.mjs --kind preview|callsheet --manifest <abs.json> --out <abs path>
// Exit code 0 on success; on failure prints one line "render-error: <reason>" to stderr and exits 1.
// The bundle is built once and cached in render/.bundle (rebuilt when src/ changes).
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { callSheetSchema, LIMITS, previewSchema } from "./src/schema.ts";

const here = dirname(fileURLToPath(import.meta.url));
const MAX_MANIFEST_BYTES = LIMITS.manifestBytes;

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
  // The preview draws the Control Room's set models, so their code is part of the bundle.
  walk(join(here, "..", "ui", "src", "sets"));
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

// Strict validation here, not in Remotion: Remotion would merge the studio defaultProps into
// missing fields and render sample data as if it were real.
const parsed = (kind === "preview" ? previewSchema : callSheetSchema).safeParse(inputProps);
if (!parsed.success) {
  const issue = parsed.error.issues[0];
  fail(`invalid ${kind} props at ${issue.path.join(".") || "(root)"}: ${issue.message}`);
}
inputProps = parsed.data;

// We own the browser so we can close it: Remotion's exit-time cleanup can hang on Windows,
// leaving the CLI alive after the file is written.
let browser;
let code = 0;
try {
  const serveUrl = await getBundle();
  const id = kind === "preview" ? "Preview" : "CallSheet";
  browser = await openBrowser("chrome");
  // selectComposition and the render get the same validated props.
  const composition = await selectComposition({ serveUrl, id, inputProps, puppeteerInstance: browser });
  mkdirSync(dirname(resolve(out)), { recursive: true });
  if (kind === "preview") {
    await renderMedia({ composition, serveUrl, codec: "h264", outputLocation: resolve(out), inputProps, crf: 20, pixelFormat: "yuv420p", concurrency: 4, timeoutInMilliseconds: 60000, puppeteerInstance: browser });
  } else {
    await renderStill({ composition, serveUrl, output: resolve(out), inputProps, imageFormat: "png", puppeteerInstance: browser });
  }
  process.stdout.write(`rendered ${kind} ${resolve(out)}\n`);
} catch (e) {
  process.stderr.write(`render-error: ${String(e?.message ?? e).split("\n")[0].slice(0, 300)}\n`);
  code = 1;
} finally {
  await Promise.race([browser?.close({ silent: true }).catch(() => {}), new Promise((r) => setTimeout(r, 5000))]);
  killOwnBrowsers();
  process.exit(code);
}

// Ends only the headless browser processes this CLI started (direct children of this PID),
// with their subtrees. Without this, Chrome's slow shutdown outlives the CLI for a minute or two.
function killOwnBrowsers() {
  if (process.platform !== "win32") return;
  try {
    const out = execFileSync(
      "powershell",
      ["-NoProfile", "-Command", `Get-CimInstance Win32_Process -Filter "ParentProcessId=${process.pid} AND Name='chrome-headless-shell.exe'" | ForEach-Object { $_.ProcessId }`],
      { encoding: "utf8", timeout: 8000, windowsHide: true },
    );
    for (const pid of out.split(/\s+/).filter((s) => /^\d+$/.test(s))) {
      try {
        execFileSync("taskkill", ["/F", "/T", "/PID", pid], { stdio: "ignore", timeout: 5000, windowsHide: true });
      } catch {
        // Already gone.
      }
    }
  } catch {
    // Best effort: never turn a finished render into a failure.
  }
}
