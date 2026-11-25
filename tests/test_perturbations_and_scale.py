"""Tests for perturbation robustness suite, scale stress-test, and attempted accuracy splits."""

from pathlib import Path

from vtf.benchmark import run_benchmark
from vtf.evaluators import BaseEvaluator
from vtf.factory import TaskFactory
from vtf.perturbations import perturb_dataset
from vtf.scale import run_scale_benchmark
from vtf.schema import TaskPackage


class _PartialQuotaMockEvaluator(BaseEvaluator):
    """Mock evaluator that fails one task with a transient api_error."""

    model_name = "mock_quota_vlm"
    provider = "gemini"
    uses_image = True

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        if task.task_id.endswith("_cf"):
            raise RuntimeError("Client error '429 Too Many Requests'")
        return f'{{"answer": "{task.answer}"}}'


def test_perturbations_preserve_manifest_and_validate(tmp_path: Path) -> None:
    src = tmp_path / "src"
    TaskFactory(src).generate_batch(families=["charts", "blueprints_gauges"], per_cell=1, base_seed=77)
    for mode in ("scan_tilt", "low_contrast_jpeg"):
        dst = tmp_path / f"out_{mode}"
        res = perturb_dataset(src, dst, mode=mode, limit=4)
        assert res["total_tasks"] == 4
        assert res["valid_tasks"] == 4


def test_scale_benchmark_generates_unique_valid_batch(tmp_path: Path) -> None:
    out_json = tmp_path / "scale.json"
    # 5 families x 3 difficulties x 1 base + 15 twins = 30 tasks fast check in pytest
    rep = run_scale_benchmark(per_cell=1, base_seed=555, out_path=out_json)
    assert rep["valid_tasks"] == 30
    assert rep["zero_hash_collisions"] is True
    assert rep["validation_pass_rate"] == 1.0
    assert out_json.exists()


def test_attempted_accuracy_separates_api_errors(tmp_path: Path) -> None:
    ds = tmp_path / "ds"
    TaskFactory(ds).generate_batch(families=["charts"], difficulties=["easy"], per_cell=1, base_seed=88)
    summary = run_benchmark(ds, evaluators=[_PartialQuotaMockEvaluator()], use_cache=False)
    assert summary.overall_accuracy["mock_quota_vlm"] == 0.5
    assert summary.attempted_accuracy["mock_quota_vlm"] == 1.0
    assert summary.attempted_counts["mock_quota_vlm"] == "1/1"
    assert summary.error_taxonomy["mock_quota_vlm"]["api_quota_error"] == 1
