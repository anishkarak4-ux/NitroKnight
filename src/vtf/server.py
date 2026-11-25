"""FastAPI backend + interactive Studio UI 2.0 for Visual Task Factory."""

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


app = FastAPI(title="Visual Task Factory Studio", version="0.2.0")


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
    header { padding: 14px 22px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #0f162b; }
    header h1 { margin: 0; font-size: 1.15rem; letter-spacing: 0.02em; }
    .pill { background: #1e293b; border: 1px solid var(--border); padding: 4px 10px; border-radius: 999px; font-size: 0.78rem; color: var(--muted); }
    .container { display: grid; grid-template-columns: 340px 1fr; min-height: calc(100vh - 56px); }
    aside { border-right: 1px solid var(--border); padding: 14px; overflow-y: auto; max-height: calc(100vh - 56px); }
    main { padding: 18px; overflow-y: auto; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 14px; }
    .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    label { font-size: 0.76rem; color: var(--muted); display: block; margin-bottom: 4px; }
    select, input, button { background: #0f162b; color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 6px 9px; font-size: 0.83rem; }
    button { background: var(--accent); border-color: var(--accent); cursor: pointer; font-weight: 600; }
    button.secondary { background: #1e293b; border-color: var(--border); }
    button:disabled { opacity: 0.5; cursor: wait; }
    .task-item { padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 7px; cursor: pointer; background: #0f162b; }
    .task-item.active { border-color: var(--accent); background: #172554; }
    .task-item .meta { font-size: 0.73rem; color: var(--muted); margin-top: 3px; }
    .viewer-grid { display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-start; }
    .viewer { position: relative; display: inline-block; max-width: 100%; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff; }
    .viewer img { display: block; max-width: 100%; height: auto; }
    .viewer svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
    .gate { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1e293b; font-size: 0.83rem; }
    .badge-ok { color: var(--ok); font-weight: 700; }
    .badge-bad { color: var(--bad); font-weight: 700; }
    pre { background: #0b1020; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 0.77rem; border: 1px solid var(--border); white-space: pre-wrap; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th, td { border-bottom: 1px solid var(--border); padding: 6px 8px; text-align: left; }
  </style>
</head>
<body>
<header>
  <h1>Visual Task Factory — Verification &amp; Benchmark Studio</h1>
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
          <option value="charts">charts (Financial / Unlabeled)</option>
          <option value="spatial_inventory">spatial_inventory (Warehouse / CLEVR)</option>
          <option value="logic_circuits">logic_circuits (Schematics / Flow)</option>
          <option value="structured_docs">structured_docs (Invoices / Redacted)</option>
          <option value="blueprints_gauges">blueprints_gauges (Floorplans / Gauges)</option>
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
        <div style="width:88px;">
          <label>Seed</label>
          <input id="genSeed" type="number" value="777" style="width:100%;" />
        </div>
      </div>
      <button id="genBtn" style="width:100%;" onclick="generateLive()">Generate + 5-Gate Validate</button>
    </div>

    <div class="card">
      <div style="font-weight:700;margin-bottom:8px;">Filter Tasks</div>
      <div class="row" style="margin-bottom:8px;">
        <select id="fltFam" style="flex:1;" onchange="renderTaskList()">
          <option value="">All Families</option>
          <option value="charts">charts</option>
          <option value="spatial_inventory">spatial_inventory</option>
          <option value="logic_circuits">logic_circuits</option>
          <option value="structured_docs">structured_docs</option>
          <option value="blueprints_gauges">blueprints_gauges</option>
        </select>
        <select id="fltDiff" style="width:95px;" onchange="renderTaskList()">
          <option value="">All Diffs</option>
          <option value="easy">easy</option>
          <option value="medium">medium</option>
          <option value="hard">hard</option>
        </select>
      </div>
      <label style="display:flex;align-items:center;gap:6px;margin:0;cursor:pointer;">
        <input type="checkbox" id="fltFailOnly" onchange="renderTaskList()" /> VLM Failures Only
      </label>
    </div>

    <div style="font-weight:700;margin-bottom:8px;">Tasks (<span id="shownCount">0</span>)</div>
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
          <div class="meta" id="tMeta" style="color:var(--muted);font-size:0.8rem;"></div>
        </div>
        <div class="row">
          <label style="display:flex;align-items:center;gap:6px;margin:0;cursor:pointer;">
            <input type="checkbox" id="toggleTwin" onchange="selectTask(STATE.selected)" /> Side-by-Side Twin
          </label>
          <label style="display:flex;align-items:center;gap:6px;margin:0;cursor:pointer;">
            <input type="checkbox" id="toggleBoxes" checked onchange="renderOverlay()" /> Show Grounding Boxes
          </label>
        </div>
      </div>
      <p id="tQuestion" style="font-size:0.98rem;background:#0f162b;padding:10px;border-radius:6px;border:1px solid var(--border);"></p>
      <div class="row" style="margin-bottom:12px;">
        <span class="pill" id="tAnswer">Answer: -</span>
        <span class="pill" id="tReason">Reasoning: -</span>
        <span class="pill" id="tCf" style="display:none;"></span>
      </div>
      <div class="viewer-grid">
        <div style="flex:1;min-width:340px;">
          <div class="viewer" id="viewerWrap">
            <img id="tImg" src="" alt="Task image" onload="renderOverlay()" />
            <svg id="tOverlay"></svg>
          </div>
        </div>
        <div id="twinWrap" style="flex:1;min-width:340px;display:none;">
          <div class="pill" id="twinLabel" style="margin-bottom:6px;display:inline-block;"></div>
          <div class="viewer">
            <img id="twinImg" src="" alt="Counterfactual twin" />
          </div>
        </div>
      </div>
    </div>

    <div class="card" id="taskPredsCard" style="display:none;">
      <div style="font-weight:700;margin-bottom:8px;">Per-Model Evaluation Responses on Selected Task</div>
      <div id="taskPreds"></div>
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

function vlmFailedTask(tid) {
  if (!STATE.report || !STATE.report.predictions) return false;
  return STATE.report.predictions.some(
    p => p.task_id === tid && !p.correct && !['diagnostic_baseline','diagnostic_oracle','blind_llm_audit'].includes(p.provider)
  );
}

function findCounterfactualPartner(t) {
  if (!t) return null;
  if (t.counterfactual_of) return STATE.tasks.find(x => x.task_id === t.counterfactual_of) || null;
  return STATE.tasks.find(x => x.counterfactual_of === t.task_id) || null;
}

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
  const fam = document.getElementById('fltFam').value;
  const diff = document.getElementById('fltDiff').value;
  const failOnly = document.getElementById('fltFailOnly').checked;
  const filtered = STATE.tasks.filter(t => {
    if (fam && t.family !== fam) return false;
    if (diff && t.difficulty !== diff) return false;
    if (failOnly && !vlmFailedTask(t.task_id)) return false;
    return true;
  });
  document.getElementById('shownCount').textContent = filtered.length;
  const el = document.getElementById('taskList');
  el.innerHTML = '';
  filtered.forEach(t => {
    const d = document.createElement('div');
    const failed = vlmFailedTask(t.task_id);
    d.className = 'task-item' + (STATE.selected && STATE.selected.task_id === t.task_id ? ' active' : '');
    d.onclick = () => selectTask(t);
    d.innerHTML = `<div style="font-weight:600;font-size:0.83rem;">${t.task_id}${failed ? ' <span style="color:#ef4444;">[VLM Fail]</span>' : ''}</div>
      <div class="meta">${t.family} · ${t.difficulty} · ${t.subtype}${t.counterfactual_of ? ' · CF-Twin' : ''}</div>`;
    el.appendChild(d);
  });
}

function selectTask(t) {
  if (!t) return;
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

  const twinWrap = document.getElementById('twinWrap');
  const partner = document.getElementById('toggleTwin').checked ? findCounterfactualPartner(t) : null;
  if (partner) {
    twinWrap.style.display = 'block';
    document.getElementById('twinLabel').textContent = `Partner: ${partner.task_id} | Answer: ${partner.answer}`;
    document.getElementById('twinImg').src = `/api/images/${partner.image_path.split('/').pop()}?v=${partner.image_sha256.slice(0,8)}`;
  } else {
    twinWrap.style.display = 'none';
  }

  const predCard = document.getElementById('taskPredsCard');
  const preds = (STATE.report?.predictions || []).filter(p => p.task_id === t.task_id);
  if (preds.length) {
    predCard.style.display = 'block';
    document.getElementById('taskPreds').innerHTML = `<table>
      <thead><tr><th>Model</th><th>Status</th><th>Predicted</th><th>Expected</th><th>Latency</th><th>Response Excerpt</th></tr></thead>
      <tbody>${preds.map(p => `<tr>
        <td><code>${p.model_name}</code></td>
        <td><span class="${p.correct ? 'badge-ok' : 'badge-bad'}">${p.correct ? 'PASS' : (p.error_category || 'FAIL')}</span></td>
        <td><code>${p.extracted_answer || '-'}</code></td>
        <td><code>${p.expected_answer}</code></td>
        <td>${p.latency_ms}ms</td>
        <td style="max-width:340px;overflow:hidden;text-overflow:ellipsis;">${(p.raw_response || p.notes || '').replace(/</g,'&lt;').slice(0,140)}</td>
      </tr>`).join('')}</tbody></table>`;
  } else {
    predCard.style.display = 'none';
  }

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
  const fams = ['charts','spatial_inventory','logic_circuits','structured_docs','blueprints_gauges'];
  const rows = (r.models_evaluated || []).map(m => {
    const fam = r.by_family[m] || {};
    const hr = r.hallucination_rate?.[m];
    const fCells = fams.map(f => `<td>${fam[f] !== undefined ? (fam[f]*100).toFixed(0)+'%' : '-'}</td>`).join('');
    return `<tr><td><code>${m}</code></td>
      <td>${((r.overall_accuracy[m]||0)*100).toFixed(1)}%</td>
      <td>${((r.counterfactual_consistency[m]||0)*100).toFixed(1)}%</td>
      <td>${hr !== undefined ? (hr*100).toFixed(0)+'%' : 'N/A'}</td>
      ${fCells}</tr>`;
  }).join('');
  document.getElementById('evalSummary').innerHTML = `<table>
    <thead><tr><th>Model</th><th>Overall</th><th>CF Consistency</th><th>Hallucination</th><th>Charts</th><th>Spatial</th><th>Circuits</th><th>Docs</th><th>Blueprints</th></tr></thead>
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
