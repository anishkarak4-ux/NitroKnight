"""Coverage tests across all 4 families x 3 difficulty levels + counterfactual twins."""

from pathlib import Path

import pytest

from vtf.factory import TaskFactory
from vtf.families import get_family
from vtf.schema import Difficulty, FamilyName
from vtf.validator import validate_task


@pytest.mark.parametrize("family", list(FamilyName))
@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_all_families_generate_valid_tasks_and_twins(
    tmp_path: Path, family: FamilyName, difficulty: Difficulty
) -> None:
    factory = TaskFactory(tmp_path)
    task, _ = factory.generate_one(family, difficulty, seed=512)
    assert task.validation is not None
    assert task.validation.valid, f"{family}/{difficulty} failed: {task.validation.rejection_reasons}"
    assert task.validation.grounding_coverage == 1.0
    assert (tmp_path / task.image_path).exists()

    fam_impl = get_family(family)
    cf = fam_impl.make_counterfactual_spec(task.ground_truth_spec, seed=529)
    assert cf is not None, f"Expected counterfactual support for {family}/{difficulty}/{task.subtype}"
    twin_spec, delta = cf
    twin = fam_impl.build_task(
        529,
        difficulty,
        factory.images_dir,
        task_id=f"{task.task_id}_cf",
        spec_override=twin_spec,
        counterfactual_of=task.task_id,
        counterfactual_delta=delta,
    )
    rep = validate_task(twin, fam_impl, tmp_path / twin.image_path)
    assert rep.valid, f"Counterfactual invalid: {rep.rejection_reasons}"
    assert str(twin.answer) != str(task.answer), "Counterfactual failed to flip verified answer"
