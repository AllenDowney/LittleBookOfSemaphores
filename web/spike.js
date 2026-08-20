/**
 * Task 4 spike: Pyodide + sync_core (no full Sync UI).
 *
 * Serve from the repo root so ../code/ is fetchable, e.g.:
 *   python -m http.server 8000
 * then open http://localhost:8000/web/spike.html
 */

const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/";

const statusEl = document.getElementById("status");
const bareOut = document.getElementById("bare-out");
const syncOut = document.getElementById("sync-out");
const rerunBtn = document.getElementById("rerun");

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind || "";
}

function formatError(err) {
  if (err == null) {
    return String(err);
  }
  if (typeof err === "string") {
    return err;
  }
  const parts = [err.message || err.name || err.toString()];
  if (err.errno != null) {
    parts.push(`errno=${err.errno}`);
  }
  if (err.code != null) {
    parts.push(`code=${err.code}`);
  }
  if (err.stack) {
    parts.push(err.stack);
  }
  return parts.join("\n");
}

async function loadText(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}: ${res.status} ${res.statusText}`);
  }
  return res.text();
}

function codeUrl(relPath) {
  // Resolve against this module so paths work from /web/spike.js
  return new URL(relPath, import.meta.url).href;
}

async function runBareChecks(pyodide) {
  const result = pyodide.runPython(`
import json

ns = {}
code = compile("x = 1 + 1", "<spike>", "exec")
exec(code, ns)
flag = eval("x == 2", ns)
# Sync-style conditional header uses eval on the condition expression
cond = eval("counter == 0", {"counter": 0})
json.dumps({"x": ns["x"], "flag": flag, "cond": cond, "ok": flag and cond})
`);
  return JSON.parse(result);
}

async function installSyncCore(pyodide) {
  const coreUrl = codeUrl("../code/sync_core.py");
  const mutexUrl = codeUrl("../code/sync_code/mutex.py");
  console.log("Fetching", coreUrl, mutexUrl);

  const coreSrc = await loadText(coreUrl);
  const mutexSrc = await loadText(mutexUrl);

  // Absolute paths in the Pyodide virtual FS
  try {
    pyodide.FS.mkdir("/sync_code");
  } catch (err) {
    // Directory may already exist on re-run
    if (!(err && (err.errno === 20 || err.code === "EEXIST"))) {
      console.warn("mkdir /sync_code:", formatError(err));
    }
  }

  pyodide.FS.writeFile("/sync_core.py", coreSrc);
  pyodide.FS.writeFile("/sync_code/mutex.py", mutexSrc);

  pyodide.runPython(`
import sys
if "/" not in sys.path:
    sys.path.insert(0, "/")
`);
}

async function runSyncStep(pyodide) {
  // Capture print() from the simulator; return get_state() plus step markers.
  const result = pyodide.runPython(`
import io
import json
from contextlib import redirect_stdout

import sync_core
from sync_core import Simulator, Thread

sync_core.SIM_LOCALS.clear()

buf = io.StringIO()
with redirect_stdout(buf):
    sim = Simulator.from_file("/sync_code/mutex.py")
    state0 = sim.get_state()
    thread_a = sim.get_threads()[0]
    source1 = thread_a.step()
    thread_b = Thread(thread_a.column)
    source2 = thread_b.step()
    state1 = sim.get_state()

payload = {
    "after_init": state0,
    "after_steps": state1,
    "source1": source1,
    "source2": source2,
    "stdout": buf.getvalue(),
    "ok": (
        source1 == "mutex.wait()"
        and source2 == "mutex.wait()"
        and state1["threads"][0]["blocked"] is False
        and state1["threads"][1]["blocked"] is True
        and state1["threads"][1]["waiting_on"] == "mutex"
        and state1["semaphores"]["mutex"]["queue"] == ["B"]
    ),
}
json.dumps(payload)
`);
  return JSON.parse(result);
}

async function runSpike() {
  rerunBtn.disabled = true;
  setStatus("Loading Pyodide…");
  bareOut.textContent = "(running)";
  syncOut.textContent = "(running)";

  try {
    const { loadPyodide } = await import(`${PYODIDE_CDN}pyodide.mjs`);
    const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });

    setStatus("Running bare compile/exec/eval…");
    const bare = await runBareChecks(pyodide);
    bareOut.textContent = JSON.stringify(bare, null, 2);
    if (!bare.ok) {
      throw new Error("Bare compile/exec/eval check failed");
    }

    setStatus("Loading sync_core into Pyodide FS…");
    await installSyncCore(pyodide);

    setStatus("Running sync_core mutex step…");
    const sync = await runSyncStep(pyodide);
    syncOut.textContent = JSON.stringify(sync, null, 2);
    if (!sync.ok) {
      throw new Error("sync_core mutex step expectations failed");
    }

    setStatus("Spike OK — compile/exec/eval and sync_core work under Pyodide.", "ok");
  } catch (err) {
    console.error(err);
    const msg = formatError(err);
    setStatus(`Spike failed: ${err.message || msg}`, "err");
    if (bareOut.textContent === "(running)") {
      bareOut.textContent = msg;
    }
    if (syncOut.textContent === "(running)" || syncOut.textContent.startsWith("[object")) {
      syncOut.textContent = msg;
    }
  } finally {
    rerunBtn.disabled = false;
  }
}

rerunBtn.addEventListener("click", runSpike);
runSpike();
