"""FastAPI backend + self-contained interactive Studio UI for Visual Task Factory."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from vtf.benchmark import run_benchmark
from vtf.evaluators import build_evaluator
from vtf.factory import TaskFactory
from vtf.families import get_family
from vtf.schema import Difficulty, FamilyName
from vtf.validator import validate_task


def _dataset_dir() -> Path:
    raw = os.getenv("VTF_DATASET_DIR", "outputs/demo_suite")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


app = FastAPI(title="Visual Task Factory Studio", version="0.1.0")


class GenerateRequest(BaseModel):
    family: FamilyName = FamilyName.CHARTS
    difficulty: Difficulty = Difficulty.MEDIUM
    seed: int = 123
    with_counterfactual: bool = True


class EvaluateRequest(BaseModel):
    models: list[str] = ["blind_prior", "pixel_heuristic", "oracle"]
    limit: int | None = None


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return STUDIO_HTML


@app.get("/api/tasks")
def list_tasks() -> dict[str, Any]:
    ds = _dataset_dir()
    tasks = TaskFactory.load_tasks(ds)
    report_path = ds / "benchmark_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    summary_path = ds / "dataset_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    return {
        "dataset_dir": str(ds),
        "summary": summary,
        "report": report,
        "tasks": [t.model_dump(mode="json") for t in tasks],
    }


@app.get("/api/images/{filename}")
def get_image(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    path = _dataset_dir() / "images" / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png")


@app.post("/api/generate-one")
def generate_one(req: GenerateRequest) -> dict[str, Any]:
    ds = _dataset_dir()
    factory = TaskFactory(ds)
    existing = TaskFactory.load_tasks(ds)
    base_task, rejected = factory.generate_one(req.family, req.difficulty, req.seed)
    new_tasks = [base_task]

    if req.with_counterfactual:
        fam_impl = get_family(req.family)
        cf_res = fam_impl.make_counterfactual_spec(base_task.ground_truth_spec, req.seed + 17)
        if cf_res is not None:
            twin_spec, delta_desc = cf_res
            twin = fam_impl.build_task(
                req.seed + 17,
                req.difficulty,
                factory.images_dir,
                task_id=f"{base_task.task_id}_cf",
                spec_override=twin_spec,
                counterfactual_of=base_task.task_id,
                counterfactual_delta=delta_desc,
            )
            twin.validation = validate_task(twin, fam_impl, ds / twin.image_path)
            if twin.validation.valid and str(twin.answer) != str(base_task.answer):
                new_tasks.append(twin)

    existing_ids = {t.task_id for t in existing}
    merged = existing + [t for t in new_tasks if t.task_id not in existing_ids]
    factory.save_dataset(merged, rejected)
    return {
        "generated": [t.model_dump(mode="json") for t in new_tasks],
        "rejected": rejected,
    }


@app.post("/api/evaluate")
def evaluate_dataset(req: EvaluateRequest) -> dict[str, Any]:
    ds = _dataset_dir()
    tasks = TaskFactory.load_tasks(ds)
    if not tasks:
        raise HTTPException(status_code=400, detail="Dataset is empty; generate tasks first.")
    try:
        evaluators = [build_evaluator(m) for m in req.models]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    summary = run_benchmark(ds, evaluators=evaluators, limit=req.limit)
    return summary.model_dump(mode="json")


STUDIO_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Visual Task Factory — Studio</title>
  <style>
    :root {
      --bg: #0b1020; --card: #131b31; --border: #253256;
      --text: #e2e8f0; --muted: #94a3b8; --accent: #3b82f6;
      --ok: #22c55e; --bad: #ef4444; --warn: #f59e0b;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); }
    header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #0f162b; }
    header h1 { margin: 0; font-size: 1.15rem; letter-spacing: 0.02em; }
    .pill { background: #1e293b; border: 1px solid var(--border); padding: 4px 10px; border-radius: 999px; font-size: 0.8rem; color: var(--muted); }
    .container { display: grid; grid-template-columns: 330px 1fr; min-height: calc(100vh - 58px); }
    aside { border-right: 1px solid var(--border); padding: 16px; overflow-y: auto; max-height: calc(100vh - 58px); }
    main { padding: 20px; overflow-y: auto; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 16px; }
    .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    label { font-size: 0.78rem; color: var(--muted); display: block; margin-bottom: 4px; }
    select, input, button { background: #0f162b; color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 7px 10px; font-size: 0.85rem; }
    button { background: var(--accent); border-color: var(--accent); cursor: pointer; font-weight: 600; }
    button.secondary { background: #1e293b; border-color: var(--border); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .task-item { padding: 9px 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; cursor: pointer; background: #0f162b; }
    .task-item.active { border-color: var(--accent); background: #172554; }
    .task-item .meta { font-size: 0.75rem; color: var(--muted); margin-top: 3px; }
    .viewer { position: relative; display: inline-block; max-width: 100%; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff; }
    .viewer img { display: block; max-width: 100%; height: auto; }
    .viewer svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
    .gate { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1e293b; font-size: 0.85rem; }
    .badge-ok { color: var(--ok); font-weight: 700; }
    .badge-bad { color: var(--bad); font-weight: 700; }
    pre { background: #0b1020; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 0.78rem; border: 1px solid var(--border); }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th, td { border-bottom: 1px solid var(--border); padding: 7px 8px; text-align: left; }
  </style>
</head>
<body>
<header>
  <h1>Visual Task Factory — Verification & Benchmark Studio</h1>
  <div class="row">
    <span class="pill" id="statsPill">Loading dataset...</span>
    <button class="secondary" onclick="runBaselineEval()">Run Offline Baselines</button>
  </div>
</header>
<div class="container">
  <aside>
    <div class="card">
      <div style="font-weight:700;margin-bottom:8px;">Generate Live Task</div>
      <div style="margin-bottom:8px;">
        <label>Family</label>
        <select id="genFamily" style="width:100%;">
          <option value="charts">charts (Financial / Ops)</option>
          <option value="spatial_inventory">spatial_inventory (Warehouse / CLEVR)</option>
          <option value="logic_circuits">logic_circuits (Schematics / Flow)</option>
          <option value="structured_docs">structured_docs (Invoices / QA)</option>
        </select>
      </div>
      <div class="row" style="margin-bottom:10px;">
        <div style="flex:1;">
          <label>Difficulty</label>
          <select id="genDiff" style="width:100%;">
            <option value="easy">easy</option>
            <option value="medium" selected>medium</option>
            <option value="hard">hard</option>
          </select>
        </div>
        <div style="width:90px;">
          <label>Seed</label>
          <input id="genSeed" type="number" value="777" style="width:100%;" />
        </div>
      </div>
      <button id="genBtn" style="width:100%;" onclick="generateLive()">Generate + 5-Gate Validate</button>
    </div>
    <div style="font-weight:700;margin-bottom:8px;">Generated Tasks</div>
    <div id="taskList"></div>
  </aside>
  <main>
    <div class="card" id="evalSummaryCard" style="display:none;">
      <div style="font-weight:700;margin-bottom:8px;">Benchmark Results</div>
      <div id="evalSummary"></div>
    </div>
    <div class="card" id="taskDetailCard">
      <div class="row" style="justify-content:space-between;margin-bottom:10px;">
        <div>
          <strong id="tTitle">Select a task</strong>
          <div class="meta" id="tMeta" style="color:var(--muted);font-size:0.82rem;"></div>
        </div>
        <div class="row">
          <label style="display:flex;align-items:center;gap:6px;margin:0;cursor:pointer;">
            <input type="checkbox" id="toggleBoxes" checked onchange="renderOverlay()" /> Show Grounding Boxes
          </label>
        </div>
      </div>
      <p id="tQuestion" style="font-size:1rem;background:#0f162b;padding:10px;border-radius:6px;border:1px solid var(--border);"></p>
      <div class="row" style="margin-bottom:12px;">
        <span class="pill" id="tAnswer">Answer: -</span>
        <span class="pill" id="tReason">Reasoning: -</span>
        <span class="pill" id="tCf" style="display:none;"></span>
      </div>
      <div class="viewer" id="viewerWrap">
        <img id="tImg" src="" alt="Task image" onload="renderOverlay()" />
        <svg id="tOverlay"></svg>
      </div>
    </div>
    <div class="row" style="align-items:stretch;">
      <div class="card" style="flex:1;min-width:300px;">
        <div style="font-weight:700;margin-bottom:8px;">5-Gate Automated Validation</div>
        <div id="tGates"></div>
      </div>
      <div class="card" style="flex:1;min-width:300px;">
        <div style="font-weight:700;margin-bottom:8px;">Independent Symbolic Solver Trace</div>
        <pre id="tTrace"></pre>
      </div>
    </div>
  </main>
</div>
<script>
let STATE = { tasks: [], selected: null, report: null };

async function loadTasks(selectId = null) {
  const res = await fetch('/api/tasks');
  const data = await res.json();
  STATE.tasks = data.tasks || [];
  STATE.report = data.report;
  document.getElementById('statsPill').textContent =
    `${STATE.tasks.length} valid tasks | Dataset: ${data.dataset_dir}`;
  renderTaskList();
  renderReport();
  if (STATE.tasks.length) {
    const target = selectId ? STATE.tasks.find(t => t.task_id === selectId) : STATE.tasks[0];
    selectTask(target || STATE.tasks[0]);
  }
}

function renderTaskList() {
  const el = document.getElementById('taskList');
  el.innerHTML = '';
  STATE.tasks.forEach(t => {
    const d = document.createElement('div');
    d.className = 'task-item' + (STATE.selected && STATE.selected.task_id === t.task_id ? ' active' : '');
    d.onclick = () => selectTask(t);
    d.innerHTML = `<div style="font-weight:600;font-size:0.84rem;">${t.task_id}</div>
      <div class="meta">${t.family} · ${t.difficulty} · ${t.subtype}${t.counterfactual_of ? ' · CF-Twin' : ''}</div>`;
    el.appendChild(d);
  });
}

function selectTask(t) {
  STATE.selected = t;
  renderTaskList();
  document.getElementById('tTitle').textContent = `${t.task_id} (${t.family} / ${t.subtype})`;
  document.getElementById('tMeta').textContent = `Seed: ${t.seed} · SHA-256: ${t.image_sha256.slice(0, 12)}...`;
  document.getElementById('tQuestion').textContent = t.question;
  document.getElementById('tAnswer').textContent = `Verified Answer: ${t.answer}${t.unit ? ' ' + t.unit : ''}`;
  document.getElementById('tReason').textContent = `Reasoning: ${t.reasoning_type}`;
  const cfEl = document.getElementById('tCf');
  if (t.counterfactual_of) {
    cfEl.style.display = 'inline-block';
    cfEl.textContent = `Twin of ${t.counterfactual_of}: ${t.counterfactual_delta}`;
  } else {
    cfEl.style.display = 'none';
  }
  const fname = t.image_path.split('/').pop();
  document.getElementById('tImg').src = `/api/images/${fname}?v=${t.image_sha256.slice(0,8)}`;

  const gatesEl = document.getElementById('tGates');
  gatesEl.innerHTML = (t.validation?.gates || []).map(g =>
    `<div class="gate"><span>${g.gate_name}<br><small style="color:var(--muted)">${g.details}</small></span>
     <span class="${g.passed ? 'badge-ok' : 'badge-bad'}">${g.passed ? 'PASS' : 'FAIL'}</span></div>`
  ).join('');
  document.getElementById('tTrace').textContent = (t.solver_trace || []).join('\\n');
}

function renderOverlay() {
  const svg = document.getElementById('tOverlay');
  const t = STATE.selected;
  if (!t || !document.getElementById('toggleBoxes').checked) { svg.innerHTML = ''; return; }
  const w = t.manifest.width, h = t.manifest.height;
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  const refs = new Set(t.referenced_ids || []);
  const evs = new Set(t.answer_evidence_ids || []);
  svg.innerHTML = t.manifest.elements.filter(e => refs.has(e.id) || evs.has(e.id)).map(e => {
    const [x0, y0, x1, y1] = e.bbox;
    const isEv = evs.has(e.id);
    const col = isEv ? '#16a34a' : '#2563eb';
    return `<rect x="${x0}" y="${y0}" width="${x1-x0}" height="${y1-y0}" fill="none" stroke="${col}" stroke-width="${isEv ? 3 : 1.5}" stroke-dasharray="${isEv ? '' : '5,3'}" />`;
  }).join('');
}

function renderReport() {
  const card = document.getElementById('evalSummaryCard');
  const r = STATE.report;
  if (!r) { card.style.display = 'none'; return; }
  card.style.display = 'block';
  const rows = (r.models_evaluated || []).map(m => {
    const fam = r.by_family[m] || {};
    return `<tr><td><code>${m}</code></td>
      <td>${((r.overall_accuracy[m]||0)*100).toFixed(1)}%</td>
      <td>${((r.counterfactual_consistency[m]||0)*100).toFixed(1)}%</td>
      <td>${((fam.charts||0)*100).toFixed(0)}%</td>
      <td>${((fam.spatial_inventory||0)*100).toFixed(0)}%</td>
      <td>${((fam.logic_circuits||0)*100).toFixed(0)}%</td>
      <td>${((fam.structured_docs||0)*100).toFixed(0)}%</td></tr>`;
  }).join('');
  document.getElementById('evalSummary').innerHTML = `<table>
    <thead><tr><th>Model</th><th>Overall</th><th>CF Consistency</th><th>Charts</th><th>Spatial</th><th>Circuits</th><th>Docs</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

async function generateLive() {
  const btn = document.getElementById('genBtn');
  btn.disabled = true;
  try {
    const body = {
      family: document.getElementById('genFamily').value,
      difficulty: document.getElementById('genDiff').value,
      seed: parseInt(document.getElementById('genSeed').value, 10) || 1,
      with_counterfactual: true
    };
    const res = await fetch('/api/generate-one', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    const data = await res.json();
    document.getElementById('genSeed').value = body.seed + 1;
    await loadTasks(data.generated?.[0]?.task_id);
  } finally { btn.disabled = false; }
}

async function runBaselineEval() {
  await fetch('/api/evaluate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({models: ['blind_prior','pixel_heuristic','oracle']}) });
  await loadTasks(STATE.selected?.task_id);
}

loadTasks();
</script>
</body>
</html>
"""
