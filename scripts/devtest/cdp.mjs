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
  "--window-size=1200,900", "--hide-scrollbars", url]);
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
ws.addEventListener("message", e => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
});
function send(method, params = {}) {
  const i = ++id; ws.send(JSON.stringify({ id: i, method, params }));
  return new Promise(r => pend.set(i, r));
}
async function evaluate(expression) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result?.result?.value;
}

await send("Runtime.enable");
await new Promise(r => setTimeout(r, 1500));   // let the 52MB build parse/paginate

for (const s of JSON.parse(stepsArg || "[]")) console.log(JSON.stringify(await evaluate(s)));

if (shotPath) {
  await new Promise(r => setTimeout(r, 400));
  const { result } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(shotPath, Buffer.from(result.data, "base64"));
  console.log("screenshot -> " + shotPath);
}

ws.close(); proc.kill();
