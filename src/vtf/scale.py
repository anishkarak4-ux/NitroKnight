"""Large-scale deterministic factory throughput and zero-collision audit."""

from __future__ import annotations

import json
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

from vtf.factory import TaskFactory


def run_scale_benchmark(
    *,
    per_cell: int = 5,
    base_seed: int = 100,
    out_path: Path | str | None = None,
) -> dict[str, Any]:
    """Generate a large multi-family batch in a temp workspace and record throughput & uniqueness."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="vtf_scale_") as tmp:
        factory = TaskFactory(tmp)
        res = factory.generate_batch(
            per_cell=per_cell,
            base_seed=base_seed,
            with_counterfactuals=True,
            save_jsonl=True,
        )
    elapsed = round(time.perf_counter() - t0, 3)
    tasks = res["tasks"]
    rejected = res["rejected_candidates"]
    shas = {t.image_sha256 for t in tasks}
    by_family = dict(sorted(Counter(t.family.value for t in tasks).items()))
    by_difficulty = dict(sorted(Counter(t.difficulty.value for t in tasks).items()))

    report = {
        "per_cell": per_cell,
        "base_seed": base_seed,
        "valid_tasks": len(tasks),
        "rejected_candidates": rejected,
        "validation_pass_rate": round(len(tasks) / max(1, len(tasks) + rejected), 4),
        "unique_image_sha256": len(shas),
        "zero_hash_collisions": len(shas) == len(tasks),
        "counterfactual_pairs": sum(1 for t in tasks if t.counterfactual_of is not None),
        "elapsed_sec": elapsed,
        "throughput_tasks_per_sec": round(len(tasks) / max(1e-6, elapsed), 2),
        "by_family": by_family,
        "by_difficulty": by_difficulty,
    }
    if out_path is not None:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
