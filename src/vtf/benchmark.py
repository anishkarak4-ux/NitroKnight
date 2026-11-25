"""Benchmark runner, resumable cache, and HTML/Markdown failure analytics reports."""

from __future__ import annotations

import html
import json
import math
from collections import defaultdict
from pathlib import Path

from vtf.evaluators import BaseEvaluator, build_evaluator
from vtf.factory import TaskFactory
from vtf.schema import (
    BenchmarkSummary,
    CounterfactualPairMetrics,
    FamilyName,
    ModelPrediction,
    TaskPackage,
)


def _load_prediction_cache(cache_path: Path) -> dict[tuple[str, str], ModelPrediction]:
    cached: dict[tuple[str, str], ModelPrediction] = {}
    if not cache_path.exists():
        return cached
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pred = ModelPrediction.model_validate_json(line)
            # Reuse only non-transient predictions (retry api_error automatically)
            if pred.error_category != "api_error":
                cached[(pred.model_name, pred.task_id)] = pred
        except Exception:
            continue
    return cached


def _rewrite_cache(cache_path: Path, preds: dict[tuple[str, str], ModelPrediction]) -> None:
    with cache_path.open("w", encoding="utf-8") as f:
        for pred in preds.values():
            f.write(pred.model_dump_json() + "\n")


def run_benchmark(
    dataset_dir: Path | str,
    model_specs: list[str] | None = None,
    *,
    evaluators: list[BaseEvaluator] | None = None,
    limit: int | None = None,
    verbose: bool = False,
    use_cache: bool = True,
) -> BenchmarkSummary:
    """Evaluate models with resumable caching and write JSON/Markdown/HTML reports."""
    ds_path = Path(dataset_dir)
    tasks = TaskFactory.load_tasks(ds_path)
    if limit is not None:
        tasks = tasks[:limit]

    valid_tasks = [t for t in tasks if t.validation is None or t.validation.valid]
    eval_list = evaluators if evaluators is not None else [
        build_evaluator(spec) for spec in (model_specs or ["blind_prior", "pixel_heuristic"])
    ]

    cache_path = ds_path / "predictions_cache.jsonl"
    cache_map = _load_prediction_cache(cache_path) if use_cache else {}

    all_preds: list[ModelPrediction] = []
    preds_by_model_task: dict[str, dict[str, ModelPrediction]] = defaultdict(dict)

    for ev in eval_list:
        for idx, t in enumerate(valid_tasks, start=1):
            key = (ev.model_name, t.task_id)
            if use_cache and key in cache_map:
                pred = cache_map[key]
                from_cache = True
            else:
                pred = ev.evaluate_task(t, ds_path)
                from_cache = False
                if use_cache and pred.error_category != "api_error":
                    cache_map[key] = pred
                    with cache_path.open("a", encoding="utf-8") as cf:
                        cf.write(pred.model_dump_json() + "\n")

            all_preds.append(pred)
            preds_by_model_task[ev.model_name][t.task_id] = pred
            if verbose:
                tag = "CACHED " if from_cache else ""
                status = "OK" if pred.correct else (pred.error_category or "WRONG")
                print(
                    f"[{ev.model_name}] {idx}/{len(valid_tasks)} {t.task_id}: {tag}{status} "
                    f"(pred={pred.extracted_answer!r}, exp={pred.expected_answer!r})",
                    flush=True,
                )

    if use_cache and cache_map:
        _rewrite_cache(cache_path, cache_map)

    return summarize_predictions(
        ds_path,
        tasks,
        valid_tasks,
        [ev.model_name for ev in eval_list],
        preds_by_model_task,
    )


def summarize_predictions(
    ds_path: Path,
    tasks: list[TaskPackage],
    valid_tasks: list[TaskPackage],
    model_names: list[str],
    preds_by_model_task: dict[str, dict[str, ModelPrediction]],
) -> BenchmarkSummary:
    """Compute aggregate accuracy, Wilson CI, taxonomy, and write MD/JSON/HTML reports."""
    overall: dict[str, float] = {}
    attempted_accuracy: dict[str, float] = {}
    attempted_counts: dict[str, str] = {}
    wilson_ci_95: dict[str, tuple[float, float]] = {}
    by_family: dict[str, dict[str, float]] = {}
    by_diff: dict[str, dict[str, float]] = {}
    by_reason: dict[str, dict[str, float]] = {}
    cf_consistency: dict[str, float] = {}
    hallucination_rate: dict[str, float] = {}
    error_taxonomy: dict[str, dict[str, int]] = {}
    cf_details: list[CounterfactualPairMetrics] = []
    all_preds: list[ModelPrediction] = []

    task_map = {t.task_id: t for t in valid_tasks}
    cf_twins = [t for t in valid_tasks if t.counterfactual_of and t.counterfactual_of in task_map]
    abstention_tasks = [t for t in valid_tasks if str(t.answer) == "CANNOT_DETERMINE"]

    for mname in model_names:
        mpreds = [preds_by_model_task[mname][t.task_id] for t in valid_tasks]
        all_preds.extend(mpreds)
        overall[mname] = _acc(mpreds)
        attempted = [p for p in mpreds if p.error_category != "api_error"]
        attempted_hits = sum(1 for p in attempted if p.correct)
        attempted_accuracy[mname] = _acc(attempted)
        attempted_counts[mname] = f"{attempted_hits}/{len(attempted)}"
        wilson_ci_95[mname] = _wilson_interval(attempted_hits, len(attempted))
        by_family[mname] = _group_acc(valid_tasks, preds_by_model_task[mname], lambda t: t.family.value)
        by_diff[mname] = _group_acc(valid_tasks, preds_by_model_task[mname], lambda t: t.difficulty.value)
        by_reason[mname] = _group_acc(valid_tasks, preds_by_model_task[mname], lambda t: t.reasoning_type)

        tax: dict[str, int] = defaultdict(int)
        for p in mpreds:
            t_obj = task_map[p.task_id]
            if p.correct:
                tax["correct"] += 1
            elif p.error_category == "api_error":
                tax["api_quota_error"] += 1
            elif str(t_obj.answer) == "CANNOT_DETERMINE":
                tax["abstention_hallucination"] += 1
            elif t_obj.family == FamilyName.LOGIC_CIRCUITS:
                tax["circuit_dag_reasoning"] += 1
            elif t_obj.family == FamilyName.BLUEPRINTS_GAUGES:
                tax["blueprint_gauge_spatial"] += 1
            else:
                tax[p.error_category or "other_error"] += 1
        error_taxonomy[mname] = dict(sorted(tax.items()))

        if abstention_tasks:
            hallucinated = sum(
                1
                for t in abstention_tasks
                if not preds_by_model_task[mname][t.task_id].correct
                and preds_by_model_task[mname][t.task_id].error_category != "api_error"
            )
            hallucination_rate[mname] = round(hallucinated / len(abstention_tasks), 4)

        consistent_hits = 0
        for twin in cf_twins:
            base = task_map[twin.counterfactual_of]  # type: ignore[index]
            bp = preds_by_model_task[mname][base.task_id]
            tp = preds_by_model_task[mname][twin.task_id]
            changed = bp.extracted_answer.strip().lower() != tp.extracted_answer.strip().lower()
            cons = bp.correct and tp.correct and changed
            if cons:
                consistent_hits += 1
            cf_details.append(
                CounterfactualPairMetrics(
                    base_task_id=base.task_id,
                    twin_task_id=twin.task_id,
                    model_name=mname,
                    base_correct=bp.correct,
                    twin_correct=tp.correct,
                    prediction_changed=changed,
                    consistently_visual=cons,
                )
            )
        cf_consistency[mname] = round(consistent_hits / len(cf_twins), 4) if cf_twins else 0.0

    rej_path = ds_path / "rejected_candidates.jsonl"
    rejected_count = (
        sum(1 for ln in rej_path.read_text(encoding="utf-8").splitlines() if ln.strip())
        if rej_path.exists()
        else 0
    )

    summary = BenchmarkSummary(
        dataset_dir=str(ds_path),
        total_tasks=len(tasks),
        valid_tasks=len(valid_tasks),
        rejected_candidates=rejected_count,
        models_evaluated=model_names,
        overall_accuracy=overall,
        attempted_accuracy=attempted_accuracy,
        attempted_counts=attempted_counts,
        wilson_ci_95=wilson_ci_95,
        by_family=by_family,
        by_difficulty=by_diff,
        by_reasoning=by_reason,
        counterfactual_consistency=cf_consistency,
        hallucination_rate=hallucination_rate,
        error_taxonomy=error_taxonomy,
        predictions=all_preds,
        counterfactual_details=cf_details,
    )

    (ds_path / "benchmark_report.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (ds_path / "benchmark_report.md").write_text(format_markdown_report(summary, valid_tasks), encoding="utf-8")
    (ds_path / "benchmark_report.html").write_text(format_html_report(summary, valid_tasks), encoding="utf-8")
    return summary


def _wilson_interval(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = hits / n
    denom = 1.0 + (z * z) / n
    center = (p + (z * z) / (2.0 * n)) / denom
    half = (z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * n)) / n)) / denom
    return (round(max(0.0, center - half), 4), round(min(1.0, center + half), 4))


def _acc(preds: list[ModelPrediction]) -> float:
    return round(sum(1 for p in preds if p.correct) / len(preds), 4) if preds else 0.0


def _group_acc(
    tasks: list[TaskPackage],
    pred_map: dict[str, ModelPrediction],
    key_fn,
) -> dict[str, float]:
    buckets: dict[str, list[ModelPrediction]] = defaultdict(list)
    for t in tasks:
        buckets[key_fn(t)].append(pred_map[t.task_id])
    return {k: _acc(v) for k, v in sorted(buckets.items())}


def format_markdown_report(summary: BenchmarkSummary, tasks: list[TaskPackage]) -> str:
    lines = [
        "# Visual Task Factory — Evaluation & Validation Report",
        "",
        f"- **Dataset:** `{summary.dataset_dir}`",
        f"- **Valid Tasks:** `{summary.valid_tasks}` (Rejected invalid candidates: `{summary.rejected_candidates}`)",
        f"- **Models Evaluated:** {', '.join(f'`{m}`' for m in summary.models_evaluated)}",
        "",
        "## 1. Overall & Attempted Accuracy (with 95% Wilson CI), Counterfactual Consistency & Hallucination",
        "",
        "| Model | Strict Accuracy | Attempted Accuracy | 95% Wilson CI | CF Consistency | Hallucination Rate | API Errors |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for m in summary.models_evaluated:
        api_errs = sum(
            1 for p in summary.predictions if p.model_name == m and p.error_category == "api_error"
        )
        h_rate = summary.hallucination_rate.get(m)
        h_str = f"{h_rate * 100:.1f}%" if h_rate is not None else "N/A"
        att_acc = summary.attempted_accuracy.get(m, summary.overall_accuracy.get(m, 0.0))
        att_cnt = summary.attempted_counts.get(m, "-")
        lo, hi = summary.wilson_ci_95.get(m, (0.0, 0.0))
        lines.append(
            f"| `{m}` | {summary.overall_accuracy.get(m, 0.0)*100:.1f}% | "
            f"{att_acc*100:.1f}% ({att_cnt}) | [{lo*100:.1f}%, {hi*100:.1f}%] | "
            f"{summary.counterfactual_consistency.get(m, 0.0)*100:.1f}% | {h_str} | {api_errs} |"
        )

    lines.extend(["", "## 2. Breakdown by Visual Family", ""])
    fams = sorted({t.family.value for t in tasks})
    lines.append("| Model | " + " | ".join(fams) + " |")
    lines.append("|---|" + "|".join("---:" for _ in fams) + "|")
    for m in summary.models_evaluated:
        row = [f"{summary.by_family.get(m, {}).get(f, 0.0)*100:.1f}%" for f in fams]
        lines.append(f"| `{m}` | " + " | ".join(row) + " |")

    lines.extend(["", "## 3. Breakdown by Difficulty", ""])
    diffs = ["easy", "medium", "hard"]
    lines.append("| Model | Easy | Medium | Hard |")
    lines.append("|---|---:|---:|---:|")
    for m in summary.models_evaluated:
        row = [f"{summary.by_difficulty.get(m, {}).get(d, 0.0)*100:.1f}%" for d in diffs]
        lines.append(f"| `{m}` | " + " | ".join(row) + " |")

    lines.extend(["", "## 4. Failure Taxonomy Counts", ""])
    all_cats = sorted({cat for m in summary.models_evaluated for cat in summary.error_taxonomy.get(m, {})})
    if all_cats:
        lines.append("| Model | " + " | ".join(all_cats) + " |")
        lines.append("|---|" + "|".join("---:" for _ in all_cats) + "|")
        for m in summary.models_evaluated:
            row = [str(summary.error_taxonomy.get(m, {}).get(c, 0)) for c in all_cats]
            lines.append(f"| `{m}` | " + " | ".join(row) + " |")

    return "\n".join(lines) + "\n"


def format_html_report(summary: BenchmarkSummary, tasks: list[TaskPackage]) -> str:
    """Build a standalone self-contained HTML diagnostic report for judges."""
    fams = sorted({t.family.value for t in tasks})
    task_map = {t.task_id: t for t in tasks}
    rows_overall = []
    for m in summary.models_evaluated:
        api_errs = sum(1 for p in summary.predictions if p.model_name == m and p.error_category == "api_error")
        h_rate = summary.hallucination_rate.get(m)
        h_str = f"{h_rate * 100:.1f}%" if h_rate is not None else "N/A"
        att_acc = summary.attempted_accuracy.get(m, summary.overall_accuracy.get(m, 0.0))
        att_cnt = summary.attempted_counts.get(m, "-")
        lo, hi = summary.wilson_ci_95.get(m, (0.0, 0.0))
        fam_cells = "".join(
            f"<td>{summary.by_family.get(m, {}).get(f, 0.0)*100:.1f}%</td>" for f in fams
        )
        rows_overall.append(
            f"<tr><td><code>{html.escape(m)}</code></td>"
            f"<td><strong>{summary.overall_accuracy.get(m, 0.0)*100:.1f}%</strong></td>"
            f"<td><strong>{att_acc*100:.1f}%</strong> ({html.escape(att_cnt)})</td>"
            f"<td>[{lo*100:.1f}%, {hi*100:.1f}%]</td>"
            f"<td>{summary.counterfactual_consistency.get(m, 0.0)*100:.1f}%</td>"
            f"<td>{h_str}</td>{fam_cells}<td>{api_errs}</td></tr>"
        )

    all_cats = sorted({cat for m in summary.models_evaluated for cat in summary.error_taxonomy.get(m, {})})
    tax_headers = "".join(f"<th>{html.escape(c)}</th>" for c in all_cats)
    tax_rows = []
    for m in summary.models_evaluated:
        cells = "".join(f"<td>{summary.error_taxonomy.get(m, {}).get(c, 0)}</td>" for c in all_cats)
        tax_rows.append(f"<tr><td><code>{html.escape(m)}</code></td>{cells}</tr>")

    # Highlight up to 12 real VLM failures (non-baseline)
    fail_cards = []
    for p in summary.predictions:
        if p.provider in {"diagnostic_baseline", "diagnostic_oracle", "blind_llm_audit"}:
            continue
        if p.correct or p.error_category == "api_error":
            continue
        t = task_map.get(p.task_id)
        if not t:
            continue
        fail_cards.append(
            f"<div class='card'><h3>{html.escape(p.model_name)} failed on <code>{html.escape(t.task_id)}</code> "
            f"({html.escape(t.family.value)} / {html.escape(t.reasoning_type)})</h3>"
            f"<p><strong>Question:</strong> {html.escape(t.question)}</p>"
            f"<p><strong>Expected:</strong> <code>{html.escape(p.expected_answer)}</code> &nbsp;|&nbsp; "
            f"<strong>Predicted:</strong> <code class='bad'>{html.escape(p.extracted_answer or p.error_category or 'NONE')}</code></p>"
            f"<img src='{html.escape(t.image_path)}' alt='{html.escape(t.task_id)}' />"
            f"<pre>{html.escape(p.raw_response[:600] or p.notes)}</pre></div>"
        )
        if len(fail_cards) >= 12:
            break

    fam_headers = "".join(f"<th>{html.escape(f)}</th>" for f in fams)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>VTF Benchmark Report</title>
<style>
body{{font-family:system-ui,sans-serif;margin:28px;background:#f8fafc;color:#0f172a}}
table{{border-collapse:collapse;width:100%;background:#fff;margin-bottom:24px}}
th,td{{border:1px solid #cbd5e1;padding:8px 10px;text-align:left;font-size:13.5px}}
th{{background:#0f172a;color:#fff}}
.card{{background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:16px;margin-bottom:18px}}
.card img{{max-width:680px;display:block;border:1px solid #e2e8f0;margin:10px 0}}
.bad{{color:#dc2626;font-weight:700}}
pre{{background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;white-space:pre-wrap;font-size:12px}}
</style></head><body>
<h1>Visual Task Factory — Benchmark &amp; Failure Report</h1>
<p>Valid Tasks: <strong>{summary.valid_tasks}</strong> | Rejected Candidates: <strong>{summary.rejected_candidates}</strong></p>
<table><thead><tr><th>Model</th><th>Strict Acc</th><th>Attempted Acc</th><th>95% Wilson CI</th><th>CF Consistency</th><th>Hallucination</th>{fam_headers}<th>API Errors</th></tr></thead>
<tbody>{''.join(rows_overall)}</tbody></table>
<h2>Failure Taxonomy</h2>
<table><thead><tr><th>Model</th>{tax_headers}</tr></thead><tbody>{''.join(tax_rows)}</tbody></table>
<h2>Spotlight: Real VLM Reasoning Failure Cases</h2>
{''.join(fail_cards) if fail_cards else '<p>No VLM reasoning failures recorded in this run.</p>'}
</body></html>"""
