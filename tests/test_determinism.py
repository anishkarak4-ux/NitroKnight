"""Determinism tests: identical seeds must yield identical images, manifests, and answers."""

from pathlib import Path

from vtf.factory import TaskFactory
from vtf.schema import Difficulty, FamilyName


def test_seeded_generation_is_byte_identical(tmp_path: Path) -> None:
    for fam in FamilyName:
        d1 = TaskFactory(tmp_path / "run1")
        d2 = TaskFactory(tmp_path / "run2")
        t1, _ = d1.generate_one(fam, Difficulty.MEDIUM, seed=2026)
        t2, _ = d2.generate_one(fam, Difficulty.MEDIUM, seed=2026)

        assert t1.question == t2.question
        assert t1.answer == t2.answer
        assert t1.image_sha256 == t2.image_sha256
        assert len(t1.manifest.elements) == len(t2.manifest.elements)
