"""End-to-end integration test: 5-family factory -> validation -> cached benchmark -> FastAPI."""

from pathlib import Path

from fastapi.testclient import TestClient

from vtf.benchmark import run_benchmark
from vtf.factory import TaskFactory
from vtf.server import app


def test_e2e_factory_benchmark_and_api(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VTF_DATASET_DIR", str(tmp_path))
    factory = TaskFactory(tmp_path)
    res = factory.generate_batch(per_cell=1, base_seed=300, with_counterfactuals=True)
    # 5 families x 3 difficulties x 1 base + 15 counterfactual twins = 30 tasks
    assert res["valid_tasks"] == 30
    assert res["rejected_candidates"] == 0

    summary = run_benchmark(tmp_path, ["blind_prior", "pixel_heuristic", "oracle"])
    assert summary.valid_tasks == 30
    assert summary.overall_accuracy["oracle_spec_verifier"] == 1.0
    assert summary.attempted_accuracy["oracle_spec_verifier"] == 1.0
    assert summary.attempted_counts["oracle_spec_verifier"] == "30/30"
    assert summary.wilson_ci_95["oracle_spec_verifier"][1] == 1.0
    assert "correct" in summary.error_taxonomy["oracle_spec_verifier"]
    assert summary.counterfactual_consistency["oracle_spec_verifier"] == 1.0
    assert summary.overall_accuracy["blind_text_prior"] < 0.30
    assert summary.counterfactual_consistency["blind_text_prior"] == 0.0
    assert (tmp_path / "benchmark_report.md").exists()
    assert (tmp_path / "benchmark_report.html").exists()
    assert (tmp_path / "predictions_cache.jsonl").exists()

    client = TestClient(app)
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert "Evaluate Selected Task Live" in r_home.text
    r_report = client.get("/report")
    assert r_report.status_code == 200
    assert "Failure Taxonomy" in r_report.text
    r_tasks = client.get("/api/tasks")
    assert r_tasks.status_code == 200
    tasks_json = r_tasks.json()["tasks"]
    assert len(tasks_json) == 30
    fname = tasks_json[0]["image_path"].split("/")[-1]
    assert client.get(f"/images/{fname}").status_code == 200
    r_probe = client.post(
        "/api/evaluate-one",
        json={"task_id": tasks_json[0]["task_id"], "model": "oracle"},
    )
    assert r_probe.status_code == 200
    assert r_probe.json()["correct"] is True
