/**
 * Sync web UI (Tasks 5–7): layout + Pyodide wiring + timed Run.
 *
 * Serve from the repo root:
 *   make serve
 *   http://localhost:8000/web/index.html
 */

const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/";

const statusEl = document.getElementById("status");
const workspaceEl = document.getElementById("workspace");
const variablesEl = document.getElementById("variables");
const semaphoresEl = document.getElementById("semaphores");
const exampleSelect = document.getElementById("example-select");
const delayInput = document.getElementById("delay-ms");
const delayLabel = document.getElementById("delay-label");

const buttons = {
  init: document.getElementById("btn-init"),
  step: document.getElementById("btn-step"),
  randomStep: document.getElementById("btn-random-step"),
  run: document.getElementById("btn-run"),
  randomRun: document.getElementById("btn-random-run"),
  stop: document.getElementById("btn-stop"),
  addThread: document.getElementById("btn-add-thread"),
};

let pyodide = null;
let ready = false;
let running = false;
let runTimer = null;
let runMode = "step"; // "step" | "random"
let examplesManifest = null;
const cachedExampleFiles = new Set();

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = `status${kind ? ` ${kind}` : ""}`;
}

function formatError(err) {
  if (err == null) return String(err);
  if (typeof err === "string") return err;
  const parts = [err.message || err.name || String(err)];
  if (err.stack) parts.push(err.stack);
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
  return new URL(relPath, import.meta.url).href;
}

function setControlsEnabled(on) {
  ready = on;
  for (const btn of Object.values(buttons)) {
    if (btn === buttons.stop) {
      btn.disabled = !running;
    } else {
      btn.disabled = !on || running;
    }
  }
  exampleSelect.disabled = !on || running;
  delayInput.disabled = !on;
}

function badgeStyle(color) {
  if (!color || color === "white") return "";
  return `style="background:${color}"`;
}

function renderVariables(state) {
  const entries = Object.entries(state.variables || {});
  if (!entries.length) {
    variablesEl.innerHTML = '<span class="muted">None</span>';
    return;
  }
  variablesEl.innerHTML = entries
    .map(
      ([name, value]) =>
        `<span class="chip"><strong>${escapeHtml(name)}</strong> = ${escapeHtml(
          formatValue(value)
        )}</span>`
    )
    .join("");
}

function renderSemaphores(state) {
  const entries = Object.entries(state.semaphores || {});
  if (!entries.length) {
    semaphoresEl.innerHTML = '<span class="muted">None</span>';
    return;
  }
  semaphoresEl.innerHTML = entries
    .map(([name, sem]) => {
      const q = (sem.queue || []).join(" ");
      const fifo = sem.fifo ? " FIFO" : "";
      return `<span class="chip"><strong>${escapeHtml(name)}</strong>=${
        sem.value
      }${fifo}${
        q ? ` <span class="queue">[${escapeHtml(q)}]</span>` : ""
      }</span>`;
    })
    .join("");
}

function threadsByRow(state, columnIndex) {
  const map = new Map();
  for (const thread of state.threads || []) {
    if (thread.column !== columnIndex) continue;
    const key = thread.row == null ? -1 : thread.row;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(thread);
  }
  return map;
}

function renderColumn(title, rows, threadMap, viewMap) {
  const col = document.createElement("section");
  col.className = "column";
  col.innerHTML = `<h2 class="column-title">${escapeHtml(title)}</h2>`;

  if (!rows.length) {
    col.innerHTML += '<div class="empty-col">No rows</div>';
    return col;
  }

  rows.forEach((text, index) => {
    const row = document.createElement("div");
    row.className = "row";
    const markers = document.createElement("div");
    markers.className = "markers";
    for (const thread of threadMap.get(index) || []) {
      const blocked = thread.blocked ? " blocked" : "";
      markers.innerHTML += `<span class="badge${blocked}" title="${escapeHtml(
        thread.name
      )}${thread.blocked ? " (blocked)" : ""}" ${badgeStyle(
        thread.color
      )}>${escapeHtml(thread.name)}</span>`;
    }
    const code = document.createElement("div");
    code.className = "code";
    let html = escapeHtml(text || " ");
    if (viewMap && viewMap[index] != null) {
      html += `<span class="view-value">→ ${escapeHtml(
        formatValue(viewMap[index])
      )}</span>`;
    }
    code.innerHTML = html || "&nbsp;";
    row.append(markers, code);
    col.append(row);
  });

  return col;
}

function viewValuesByInitRow(state) {
  const map = {};
  const views = state.views || {};
  const variables = state.variables || {};
  const semaphores = state.semaphores || {};
  for (const [name, rowIndex] of Object.entries(views)) {
    if (rowIndex == null) continue;
    if (name in variables) {
      map[rowIndex] = variables[name];
    } else if (name in semaphores) {
      map[rowIndex] = semaphores[name].value;
    }
  }
  return map;
}

function renderState(state) {
  renderVariables(state);
  renderSemaphores(state);
  workspaceEl.innerHTML = "";

  const initViews = viewValuesByInitRow(state);
  workspaceEl.append(
    renderColumn("Initialization", state.init || [], new Map(), initViews)
  );

  (state.columns || []).forEach((rows, index) => {
    const label =
      (state.columns || []).length === 1
        ? "Thread code"
        : `Thread column ${index + 1}`;
    workspaceEl.append(
      renderColumn(label, rows, threadsByRow(state, index), null)
    );
  });
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatValue(value) {
  if (value !== null && typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

async function installEngine() {
  const coreSrc = await loadText(codeUrl("../code/sync_core.py"));
  try {
    pyodide.FS.mkdir("/sync_code");
  } catch (err) {
    /* may already exist */
  }
  pyodide.FS.writeFile("/sync_core.py", coreSrc);

  pyodide.runPython(`
import sys
import io
import json
from contextlib import redirect_stdout

if "/" not in sys.path:
    sys.path.insert(0, "/")

import sync_core
from sync_core import Simulator, Thread

_sim = None

def _quiet(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn()
    return result, buf.getvalue()

def load_example(name):
    global _sim
    sync_core.SIM_LOCALS.clear()
    path = "/sync_code/" + name
    def go():
        global _sim
        _sim = Simulator.from_file(path)
        return _sim.get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def load_example_source(text, filename=""):
    global _sim
    sync_core.SIM_LOCALS.clear()
    def go():
        global _sim
        _sim = Simulator.from_source(text, filename=filename)
        return _sim.get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def reinit():
    global _sim
    if _sim is None:
        raise RuntimeError("No simulation loaded")
    def go():
        # Drop live threads, then re-run init and one thread per column.
        _sim.threads.clear()
        _sim.namer = sync_core.Namer()
        sync_core.SIM_LOCALS.clear()
        _sim.locals = sync_core.SIM_LOCALS
        _sim.run_init()
        for col in _sim.cols:
            col.create_thread()
        return _sim.get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def do_step():
    def go():
        _sim.step()
        return _sim.get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def do_random_step():
    def go():
        _sim.random_step()
        return _sim.get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def do_add_thread(column_index=0):
    def go():
        _sim.create_thread(int(column_index))
        return _sim.get_state()
    state, _ = _quiet(go)
    return json.dumps(state)
`);
}

async function ensureExampleOnFs(filename) {
  if (cachedExampleFiles.has(filename)) {
    return;
  }
  const src = await loadText(codeUrl(`../code/sync_code/${filename}`));
  pyodide.FS.writeFile(`/sync_code/${filename}`, src);
  cachedExampleFiles.add(filename);
}

function populateExampleSelect(manifest) {
  exampleSelect.innerHTML = "";
  const groups = new Map();
  for (const item of manifest.examples) {
    if (!groups.has(item.group)) {
      groups.set(item.group, []);
    }
    groups.get(item.group).push(item);
  }
  for (const [group, items] of groups) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = group;
    for (const item of items) {
      const opt = document.createElement("option");
      opt.value = item.file;
      opt.textContent = item.title;
      optgroup.append(opt);
    }
    exampleSelect.append(optgroup);
  }
}

async function loadManifest() {
  const text = await loadText(codeUrl("examples.json"));
  examplesManifest = JSON.parse(text);
  populateExampleSelect(examplesManifest);
}

function applyStateJson(jsonStr) {
  const state = JSON.parse(jsonStr);
  renderState(state);
  return state;
}

async function loadSelectedExample() {
  stopRun();
  const name = exampleSelect.value;
  if (!name) {
    throw new Error("No example selected");
  }
  setStatus(`Loading ${name}…`);
  await ensureExampleOnFs(name);
  const jsonStr = pyodide.runPython(`load_example(${JSON.stringify(name)})`);
  applyStateJson(jsonStr);
  const title =
    (examplesManifest &&
      examplesManifest.examples.find((item) => item.file === name)?.title) ||
    name;
  setStatus(`Loaded ${title}`, "ok");
}

function stopRun() {
  running = false;
  if (runTimer != null) {
    clearTimeout(runTimer);
    runTimer = null;
  }
  if (ready) {
    setControlsEnabled(true);
  }
}

function scheduleNext() {
  if (!running) return;
  const delay = Number(delayInput.value) || 200;
  runTimer = setTimeout(async () => {
    runTimer = null;
    if (!running) return;
    try {
      const fn = runMode === "random" ? "do_random_step()" : "do_step()";
      const jsonStr = pyodide.runPython(fn);
      applyStateJson(jsonStr);
      scheduleNext();
    } catch (err) {
      console.error(err);
      stopRun();
      setStatus(`Run failed: ${formatError(err)}`, "err");
    }
  }, delay);
}

function startRun(mode) {
  runMode = mode;
  running = true;
  setControlsEnabled(true);
  buttons.stop.disabled = false;
  setStatus(mode === "random" ? "Random Run…" : "Run…");
  scheduleNext();
}

delayInput.addEventListener("input", () => {
  delayLabel.textContent = `${delayInput.value} ms`;
});

buttons.init.addEventListener("click", () => {
  try {
    stopRun();
    const jsonStr = pyodide.runPython("reinit()");
    applyStateJson(jsonStr);
    setStatus("Initialization complete", "ok");
  } catch (err) {
    setStatus(formatError(err), "err");
  }
});

buttons.step.addEventListener("click", () => {
  try {
    stopRun();
    const jsonStr = pyodide.runPython("do_step()");
    applyStateJson(jsonStr);
    setStatus("Step", "ok");
  } catch (err) {
    setStatus(formatError(err), "err");
  }
});

buttons.randomStep.addEventListener("click", () => {
  try {
    stopRun();
    const jsonStr = pyodide.runPython("do_random_step()");
    applyStateJson(jsonStr);
    setStatus("Random Step", "ok");
  } catch (err) {
    setStatus(formatError(err), "err");
  }
});

buttons.run.addEventListener("click", () => startRun("step"));
buttons.randomRun.addEventListener("click", () => startRun("random"));
buttons.stop.addEventListener("click", () => {
  stopRun();
  setStatus("Stopped");
});

buttons.addThread.addEventListener("click", () => {
  try {
    stopRun();
    const jsonStr = pyodide.runPython("do_add_thread(0)");
    applyStateJson(jsonStr);
    setStatus("Added thread", "ok");
  } catch (err) {
    setStatus(formatError(err), "err");
  }
});

exampleSelect.addEventListener("change", () => {
  loadSelectedExample().catch((err) => setStatus(formatError(err), "err"));
});

async function boot() {
  setControlsEnabled(false);
  setStatus("Loading Pyodide…");
  try {
    const { loadPyodide } = await import(`${PYODIDE_CDN}pyodide.mjs`);
    pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });
    setStatus("Installing sync_core…");
    await installEngine();
    await loadManifest();
    setControlsEnabled(true);
    await loadSelectedExample();
  } catch (err) {
    console.error(err);
    setStatus(`Startup failed: ${formatError(err)}`, "err");
    setControlsEnabled(false);
  }
}

boot();
