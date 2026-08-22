/**
 * Sync Quarto embed (Task 23).
 *
 * Mounts compact Sync widgets on elements:
 *   <div class="sync-embed" data-example="mutex.py"></div>
 *
 * Asset layout (next to this file):
 *   sync_core.py
 *   examples/<name>.py
 */

const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/";
const ASSET_BASE = new URL("./", import.meta.url);

let sharedPyodide = null;
let engineReady = null;
let embedSeq = 0;

function assetUrl(rel) {
  return new URL(rel, ASSET_BASE).href;
}

async function loadText(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}: ${res.status} ${res.statusText}`);
  }
  return res.text();
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

function badgeStyle(color) {
  if (!color || color === "white") return "";
  return `style="background:${color}"`;
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

function viewValuesByInitRow(state) {
  const map = {};
  const views = state.views || {};
  const variables = state.variables || {};
  const semaphores = state.semaphores || {};
  for (const [name, rowIndex] of Object.entries(views)) {
    if (rowIndex == null) continue;
    if (name in variables) map[rowIndex] = variables[name];
    else if (name in semaphores) map[rowIndex] = semaphores[name].value;
  }
  return map;
}

function renderColumn(title, rows, threadMap, viewMap) {
  const col = document.createElement("section");
  col.className = "sync-column";
  col.innerHTML = `<h3 class="sync-column-title">${escapeHtml(title)}</h3>`;
  if (!rows.length) {
    col.innerHTML += '<div class="sync-empty">No rows</div>';
    return col;
  }
  rows.forEach((text, index) => {
    const row = document.createElement("div");
    row.className = "sync-row";
    const markers = document.createElement("div");
    markers.className = "sync-markers";
    for (const thread of threadMap.get(index) || []) {
      const blocked = thread.blocked ? " blocked" : "";
      markers.innerHTML += `<span class="sync-badge${blocked}" title="${escapeHtml(
        thread.name
      )}${thread.blocked ? " (blocked)" : ""}" ${badgeStyle(
        thread.color
      )}>${escapeHtml(thread.name)}</span>`;
    }
    const code = document.createElement("div");
    code.className = "sync-code";
    let html = escapeHtml(text || " ");
    if (viewMap && viewMap[index] != null) {
      html += `<span class="sync-view">→ ${escapeHtml(
        formatValue(viewMap[index])
      )}</span>`;
    }
    code.innerHTML = html || "&nbsp;";
    row.append(markers, code);
    col.append(row);
  });
  return col;
}

function renderChips(el, entries, formatChip) {
  if (!entries.length) {
    el.innerHTML = '<span class="sync-muted">—</span>';
    return;
  }
  el.innerHTML = entries.map(formatChip).join("");
}

async function ensureEngine() {
  if (engineReady) return engineReady;
  engineReady = (async () => {
    const { loadPyodide } = await import(`${PYODIDE_CDN}pyodide.mjs`);
    sharedPyodide = await loadPyodide({ indexURL: PYODIDE_CDN });
    const coreSrc = await loadText(assetUrl("sync_core.py"));
    try {
      sharedPyodide.FS.mkdir("/sync_code");
    } catch (_) {
      /* exists */
    }
    sharedPyodide.FS.writeFile("/sync_core.py", coreSrc);
    sharedPyodide.runPython(`
import sys, io, json
from contextlib import redirect_stdout
if "/" not in sys.path:
    sys.path.insert(0, "/")
import sync_core
from sync_core import Simulator, Thread

_sims = {}
_cached_files = set()

def _quiet(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn()
    return result, buf.getvalue()

def ensure_example_bytes(name, text):
    path = "/sync_code/" + name
    if name not in _cached_files:
        with open(path, "w") as fp:
            fp.write(text)
        _cached_files.add(name)
    return path

def load_example(embed_id, name):
    sync_core.SIM_LOCALS.clear()
    path = "/sync_code/" + name
    def go():
        _sims[embed_id] = Simulator.from_file(path)
        return _sims[embed_id].get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def reinit(embed_id):
    sim = _sims[embed_id]
    def go():
        sim.threads.clear()
        sim.namer = sync_core.Namer()
        sync_core.SIM_LOCALS.clear()
        sim.locals = sync_core.SIM_LOCALS
        sim.run_init()
        for col in sim.cols:
            col.create_thread()
        return sim.get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def do_step(embed_id):
    def go():
        _sims[embed_id].step()
        return _sims[embed_id].get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def do_random_step(embed_id):
    def go():
        _sims[embed_id].random_step()
        return _sims[embed_id].get_state()
    state, _ = _quiet(go)
    return json.dumps(state)

def do_add_thread(embed_id, column_index=0):
    def go():
        _sims[embed_id].create_thread(int(column_index))
        return _sims[embed_id].get_state()
    state, _ = _quiet(go)
    return json.dumps(state)
`);
  })();
  return engineReady;
}

function buildShell(root, example) {
  root.classList.remove("sync-pending");
  root.classList.add("sync-widget");
  root.innerHTML = `
    <div class="sync-toolbar">
      <span class="sync-example-label">${escapeHtml(example)}</span>
      <button type="button" data-act="init">Run initialization</button>
      <button type="button" data-act="step">Step</button>
      <button type="button" data-act="random-step">Random Step</button>
      <button type="button" data-act="add-thread">Add thread</button>
      <span class="sync-status">Loading…</span>
    </div>
    <div class="sync-panels">
      <div><h4>Variables</h4><div class="sync-variables sync-chips"></div></div>
      <div><h4>Semaphores</h4><div class="sync-semaphores sync-chips"></div></div>
    </div>
    <div class="sync-workspace"></div>
  `;
  return {
    status: root.querySelector(".sync-status"),
    variables: root.querySelector(".sync-variables"),
    semaphores: root.querySelector(".sync-semaphores"),
    workspace: root.querySelector(".sync-workspace"),
    buttons: {
      init: root.querySelector('[data-act="init"]'),
      step: root.querySelector('[data-act="step"]'),
      randomStep: root.querySelector('[data-act="random-step"]'),
      addThread: root.querySelector('[data-act="add-thread"]'),
    },
  };
}

function setStatus(ui, text, kind) {
  ui.status.textContent = text;
  ui.status.className = `sync-status${kind ? ` ${kind}` : ""}`;
}

function setEnabled(ui, on) {
  for (const btn of Object.values(ui.buttons)) {
    btn.disabled = !on;
  }
}

function renderState(ui, state) {
  const vars = Object.entries(state.variables || {});
  renderChips(ui.variables, vars, ([name, value]) =>
    `<span class="sync-chip"><strong>${escapeHtml(name)}</strong>=${escapeHtml(
      formatValue(value)
    )}</span>`
  );
  const sems = Object.entries(state.semaphores || {});
  renderChips(ui.semaphores, sems, ([name, sem]) => {
    const q = (sem.queue || []).join(" ");
    return `<span class="sync-chip"><strong>${escapeHtml(name)}</strong>=${
      sem.value
    }${q ? ` <span class="sync-queue">[${escapeHtml(q)}]</span>` : ""}</span>`;
  });

  ui.workspace.innerHTML = "";
  ui.workspace.append(
    renderColumn(
      "Initialization",
      state.init || [],
      new Map(),
      viewValuesByInitRow(state)
    )
  );
  (state.columns || []).forEach((rows, index) => {
    const label =
      (state.columns || []).length === 1
        ? "Thread code"
        : `Thread column ${index + 1}`;
    ui.workspace.append(
      renderColumn(label, rows, threadsByRow(state, index), null)
    );
  });
}

async function mountEmbed(root) {
  const example = root.dataset.example || root.dataset.file;
  if (!example) {
    root.innerHTML =
      '<p class="sync-error">Sync embed missing data-example="…"</p>';
    return;
  }

  const embedId = root.id || `sync-embed-${++embedSeq}`;
  root.id = embedId;
  const ui = buildShell(root, example);
  setEnabled(ui, false);

  try {
    setStatus(ui, "Loading Pyodide…");
    await ensureEngine();
    const py = sharedPyodide;
    setStatus(ui, `Fetching ${example}…`);
    const src = await loadText(assetUrl(`examples/${example}`));
    py.runPython(
      `ensure_example_bytes(${JSON.stringify(example)}, ${JSON.stringify(src)})`
    );
    const stateJson = py.runPython(
      `load_example(${JSON.stringify(embedId)}, ${JSON.stringify(example)})`
    );
    renderState(ui, JSON.parse(stateJson));
    setEnabled(ui, true);
    setStatus(ui, "Ready", "ok");

    const run = (pyCall, label) => {
      try {
        const json = py.runPython(pyCall);
        renderState(ui, JSON.parse(json));
        setStatus(ui, label, "ok");
      } catch (err) {
        console.error(err);
        setStatus(ui, err.message || String(err), "err");
      }
    };

    ui.buttons.init.addEventListener("click", () =>
      run(`reinit(${JSON.stringify(embedId)})`, "Initialized")
    );
    ui.buttons.step.addEventListener("click", () =>
      run(`do_step(${JSON.stringify(embedId)})`, "Step")
    );
    ui.buttons.randomStep.addEventListener("click", () =>
      run(`do_random_step(${JSON.stringify(embedId)})`, "Random Step")
    );
    ui.buttons.addThread.addEventListener("click", () =>
      run(`do_add_thread(${JSON.stringify(embedId)}, 0)`, "Added thread")
    );
  } catch (err) {
    console.error(err);
    setStatus(ui, err.message || String(err), "err");
    root.insertAdjacentHTML(
      "beforeend",
      `<pre class="sync-error-detail">${escapeHtml(err.message || String(err))}</pre>`
    );
  }
}

export async function mountAll(selector = ".sync-embed") {
  const nodes = document.querySelectorAll(selector);
  for (const node of nodes) {
    await mountEmbed(node);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    mountAll();
  });
} else {
  mountAll();
}
