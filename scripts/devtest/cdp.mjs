// Minimal headless-browser driver for this project — no npm install needed.
//
// Uses the chrome-headless-shell binary that Playwright already downloaded, driven over the
// DevTools Protocol through Node's BUILT-IN WebSocket (Node >= 21). There is no playwright /
// puppeteer package installed in this repo, and none is needed.
//
//   node scripts/devtest/cdp.mjs <url> '[ "js expr", "js expr", ... ]'  [outfile.png]
//
// Each JS expression is evaluated in the page and its return value printed as JSON
// (promises are awaited). If a 3rd arg is given, a screenshot is saved there afterwards.
//
// Two directives may appear in the expression list instead of JS:
//   "__OFFLINE__" / "__ONLINE__"  cut or restore the network (PWA offline checks)
//   "__RELOAD__"                  reload and wait for the page to settle
//
// Example — open the test page, start reading, count rendered entries, screenshot:
//   node scripts/devtest/cdp.mjs "file://$PWD/tmp/devtest/testpage.html" \
//     '["document.getElementById(\"start\").click()","document.querySelectorAll(\".entry\").length"]' \
//     tmp/devtest/shot.png
import { spawn } from "node:child_process";
import { readdirSync, writeFileSync } from "node:fs";

const CACHE = process.env.HOME + "/Library/Caches/ms-playwright";
const dir = readdirSync(CACHE).filter(d => d.startsWith("chromium_headless_shell")).sort().pop();
const BIN = `${CACHE}/${dir}/chrome-headless-shell-mac-arm64/chrome-headless-shell`;

const [url, stepsArg, shotPath] = process.argv.slice(2);
const PORT = 9333 + (process.pid % 500);

const proc = spawn(BIN, ["--remote-debugging-port=" + PORT, "--headless", "--disable-gpu",
  "--no-sandbox", "--user-data-dir=/tmp/cdp-prof-" + Date.now(),
  "--window-size=1200,900", "--hide-scrollbars",
  // synthetic .click() isn't a real user gesture, so <audio>.play() would be blocked;
  // without these, verifying pronunciation always fails with NotAllowedError.
  "--autoplay-policy=no-user-gesture-required", "--mute-audio", url]);
proc.stderr.on("data", () => {});

async function waitTarget() {
  for (let i = 0; i < 80; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const t = list.find(x => x.type === "page" && x.webSocketDebuggerUrl);
      if (t) return t.webSocketDebuggerUrl;
    } catch {}
    await new Promise(r => setTimeout(r, 250));
  }
  throw new Error("headless shell never came up");
}

const ws = new WebSocket(await waitTarget());
await new Promise(r => ws.addEventListener("open", r));
let id = 0; const pend = new Map();
const swSessions = new Set();          // service-worker targets, attached via Target.setAutoAttach
// The page can navigate on its own (a service-worker update reloads it). Evaluating without a
// context id then silently lands in the DESTROYED context: the document looks fine but every
// global is gone, so probes fail with "window.X is undefined" and it reads like an app bug.
// Track the newest default context and always evaluate in that one.
let ctxId = null;
ws.addEventListener("message", e => {
  const m = JSON.parse(e.data);
  if (m.method === "Target.attachedToTarget" && m.params.targetInfo.type === "service_worker")
    swSessions.add(m.params.sessionId);
  if (m.method === "Target.detachedFromTarget") swSessions.delete(m.params.sessionId);
  if (m.method === "Runtime.executionContextCreated" && m.params.context.auxData?.isDefault)
    ctxId = m.params.context.id;
  if (m.method === "Runtime.executionContextDestroyed" && m.params.executionContextId === ctxId)
    ctxId = null;
  if (m.method === "Runtime.executionContextsCleared") ctxId = null;
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
});
function send(method, params = {}, sessionId) {
  const i = ++id;
  ws.send(JSON.stringify(sessionId ? { id: i, method, params, sessionId } : { id: i, method, params }));
  return new Promise(r => pend.set(i, r));
}
async function evaluate(expression, retry = 3) {
  for (let i = 0; ctxId === null && i < 100; i++)   // mid-navigation: wait for the new context
    await new Promise(r => setTimeout(r, 100));
  const p = { expression, returnByValue: true, awaitPromise: true };
  if (ctxId !== null) p.contextId = ctxId;
  const r = await send("Runtime.evaluate", p);
  // A protocol-level error is NOT a value: swallowing it as undefined is how "the app broke"
  // gets faked. The one recoverable case is the page navigating out from under a long await
  // (e.g. an update reload) — then the context is gone; wait for its replacement and retry once.
  if (r.error) {
    if (retry > 0 && /navigated|context/i.test(r.error.message || "")) {
      await new Promise(r2 => setTimeout(r2, 1500));   // let the new document install its globals
      return evaluate(expression, retry - 1);
    }
    throw new Error("CDP " + JSON.stringify(r.error) + " while evaluating: " + expression);
  }
  if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result?.result?.value;
}

await send("Runtime.enable");
await send("Network.enable");
// Auto-attach so we can reach the service-worker target too: with a SW installed, page
// requests are issued by the SW, and offline emulation set only on the page target does
// nothing — the fetch still succeeds and a cache miss looks like a hit.
await send("Target.setAutoAttach", { autoAttach: true, waitForDebuggerOnStart: false, flatten: true });
await new Promise(r => setTimeout(r, 1500));   // let the page parse/paginate (the 49MB single-file build needs it)

// Offline emulation is the only way to prove the service worker really serves from cache.
async function net(offline) {
  const cond = { offline, latency: 0, downloadThroughput: -1, uploadThroughput: -1 };
  await send("Network.emulateNetworkConditions", cond);
  for (const s of swSessions) {
    await send("Network.enable", {}, s);
    await send("Network.emulateNetworkConditions", cond, s);
  }
  return (offline ? "offline" : "online") + ` (page + ${swSessions.size} sw)`;
}

for (const s of JSON.parse(stepsArg || "[]")) {
  let out;
  if (s === "__OFFLINE__") out = await net(true);
  else if (s === "__ONLINE__") out = await net(false);
  else if (s === "__RELOAD__") {
    await send("Page.enable"); await send("Page.reload", {});
    await new Promise(r => setTimeout(r, 3000));
    out = "reloaded";
  } else out = await evaluate(s);
  console.log(JSON.stringify(out));
}

if (shotPath) {
  await new Promise(r => setTimeout(r, 400));
  const { result } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(shotPath, Buffer.from(result.data, "base64"));
  console.log("screenshot -> " + shotPath);
}

ws.close(); proc.kill();
