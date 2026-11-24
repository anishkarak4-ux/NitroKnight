"""End-to-end integration test: batch factory -> validation -> offline benchmark -> FastAPI."""

from pathlib import Path

from fastapi.testclient import TestClient

from vtf.benchmark import run_benchmark
from vtf.factory import TaskFactory
from vtf.server import app


def test_e2e_factory_benchmark_and_api(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VTF_DATASET_DIR", str(tmp_path))
    factory = TaskFactory(tmp_path)
    res = factory.generate_batch(per_cell=1, base_seed=300, with_counterfactuals=True)
    # 4 families x 3 difficulties x 1 base + 12 counterfactual twins = 24 tasks
    assert res["valid_tasks"] == 24
    assert res["rejected_candidates"] == 0

    summary = run_benchmark(tmp_path, ["blind_prior", "pixel_heuristic", "oracle"])
    assert summary.valid_tasks == 24
    # Oracle verifier proves 100% deterministic solvability
    assert summary.overall_accuracy["oracle_spec_verifier"] == 1.0
    assert summary.counterfactual_consistency["oracle_spec_verifier"] == 1.0
    # Blind text prior cannot beat low chance without pixels
    assert summary.overall_accuracy["blind_text_prior"] < 0.30
    assert summary.counterfactual_consistency["blind_text_prior"] == 0.0
    assert (tmp_path / "benchmark_report.md").exists()

    client = TestClient(app)
    r_home = client.get("/")
    assert r_home.status_code == 200
    r_tasks = client.get("/api/tasks")
    assert r_tasks.status_code == 200
    assert len(r_tasks.json()["tasks"]) == 24
