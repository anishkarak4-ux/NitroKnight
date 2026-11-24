"""Benchmark runner and diagnostic failure analytics report generator."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from vtf.evaluators import BaseEvaluator, build_evaluator
from vtf.factory import TaskFactory
from vtf.schema import (
    BenchmarkSummary,
    CounterfactualPairMetrics,
    ModelPrediction,
    TaskPackage,
)


def run_benchmark(
    dataset_dir: Path | str,
    model_specs: list[str] | None = None,
    *,
    evaluators: list[BaseEvaluator] | None = None,
    limit: int | None = None,
    verbose: bool = False,
) -> BenchmarkSummary:
    """Evaluate one or more models on a validated task dataset and write reports."""
    ds_path = Path(dataset_dir)
    tasks = TaskFactory.load_tasks(ds_path)
    if limit is not None:
        tasks = tasks[:limit]

    valid_tasks = [t for t in tasks if t.validation is None or t.validation.valid]
    eval_list = evaluators if evaluators is not None else [
        build_evaluator(spec) for spec in (model_specs or ["blind_prior", "pixel_heuristic"])
    ]

    all_preds: list[ModelPrediction] = []
    preds_by_model_task: dict[str, dict[str, ModelPrediction]] = defaultdict(dict)

    for ev in eval_list:
        for idx, t in enumerate(valid_tasks, start=1):
            pred = ev.evaluate_task(t, ds_path)
            all_preds.append(pred)
            preds_by_model_task[ev.model_name][t.task_id] = pred
            if verbose:
                status = "OK" if pred.correct else (pred.error_category or "WRONG")
                print(f"[{ev.model_name}] {idx}/{len(valid_tasks)} {t.task_id}: {status} (pred={pred.extracted_answer!r}, exp={pred.expected_answer!r})", flush=True)

    overall: dict[str, float] = {}
    by_family: dict[str, dict[str, float]] = {}
    by_diff: dict[str, dict[str, float]] = {}
    by_reason: dict[str, dict[str, float]] = {}
    cf_consistency: dict[str, float] = {}
    cf_details: list[CounterfactualPairMetrics] = []

    task_map = {t.task_id: t for t in valid_tasks}
    cf_twins = [t for t in valid_tasks if t.counterfactual_of and t.counterfactual_of in task_map]

    for ev in eval_list:
        mname = ev.model_name
        mpreds = [preds_by_model_task[mname][t.task_id] for t in valid_tasks]
        overall[mname] = _acc(mpreds)
        by_family[mname] = _group_acc(valid_tasks, preds_by_model_task[mname], lambda t: t.family.value)
        by_diff[mname] = _group_acc(valid_tasks, preds_by_model_task[mname], lambda t: t.difficulty.value)
        by_reason[mname] = _group_acc(valid_tasks, preds_by_model_task[mname], lambda t: t.reasoning_type)

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
        models_evaluated=[ev.model_name for ev in eval_list],
        overall_accuracy=overall,
        by_family=by_family,
        by_difficulty=by_diff,
        by_reasoning=by_reason,
        counterfactual_consistency=cf_consistency,
        predictions=all_preds,
        counterfactual_details=cf_details,
    )

    (ds_path / "benchmark_report.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (ds_path / "benchmark_report.md").write_text(format_markdown_report(summary, valid_tasks), encoding="utf-8")
    return summary


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
        "## 1. Overall Accuracy & Counterfactual Visual Consistency",
        "",
        "| Model | Overall Accuracy | Counterfactual Consistency | API Errors |",
        "|---|---:|---:|---:|",
    ]
    for m in summary.models_evaluated:
        api_errs = sum(
            1 for p in summary.predictions if p.model_name == m and p.error_category == "api_error"
        )
        lines.append(
            f"| `{m}` | {summary.overall_accuracy.get(m, 0.0)*100:.1f}% | "
            f"{summary.counterfactual_consistency.get(m, 0.0)*100:.1f}% | {api_errs} |"
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

    return "\n".join(lines) + "\n"
