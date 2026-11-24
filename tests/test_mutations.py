"""Tests verifying mutation testing achieves 100% fault-detection rate."""

from pathlib import Path

from vtf.mutation import run_mutation_suite


def test_mutation_suite_kills_all_injected_faults(tmp_path: Path) -> None:
    report = run_mutation_suite(work_dir=tmp_path)
    assert report["total_mutants"] == 9
    assert report["killed_mutants"] == 9
    assert report["all_killed"] is True
