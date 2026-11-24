"""Tests verifying the 5-gate validator rejects defective tasks."""

from pathlib import Path

from vtf.factory import TaskFactory
from vtf.families import get_family
from vtf.schema import AnswerType, Difficulty, FamilyName, SceneElement
from vtf.validator import validate_task


def test_validator_catches_out_of_bounds_and_ungrounded_refs(tmp_path: Path) -> None:
    factory = TaskFactory(tmp_path)
    task, _ = factory.generate_one(FamilyName.SPATIAL_INVENTORY, Difficulty.EASY, seed=77)
    fam = get_family(FamilyName.SPATIAL_INVENTORY)
    img_path = tmp_path / task.image_path

    # Inject out-of-bounds element + missing referenced ID + verbatim leak
    bad1 = task.model_copy(deep=True)
    bad1.manifest.elements.append(
        SceneElement(id="clipped_box", kind="crate", bbox=(1050.0, 10.0, 1200.0, 80.0))
    )
    rep1 = validate_task(bad1, fam, img_path)
    assert not rep1.valid
    assert any("Out-of-bounds" in r for r in rep1.rejection_reasons)

    bad2 = task.model_copy(deep=True)
    bad2.referenced_ids.append("non_existent_element")
    rep2 = validate_task(bad2, fam, img_path)
    assert not rep2.valid
    assert any("absent from image" in r for r in rep2.rejection_reasons)

    bad3 = task.model_copy(deep=True)
    bad3.answer = "SecretValue"
    bad3.answer_type = AnswerType.STRING
    bad3.question = "What is SecretValue in this image?"
    rep3 = validate_task(bad3, fam, img_path)
    assert not rep3.valid
    assert any("leaked" in r.lower() for r in rep3.rejection_reasons)


def test_validator_catches_overlapping_queried_labels(tmp_path: Path) -> None:
    factory = TaskFactory(tmp_path)
    task, _ = factory.generate_one(FamilyName.CHARTS, Difficulty.EASY, seed=101)
    fam = get_family(FamilyName.CHARTS)
    img_path = tmp_path / task.image_path

    bad = task.model_copy(deep=True)
    bad.manifest.elements.extend(
        [
            SceneElement(
                id="xtick_A", kind="axis_tick", label="A", bbox=(100.0, 500.0, 180.0, 530.0),
                font_px=14.0, is_queried_text=True,
            ),
            SceneElement(
                id="xtick_B", kind="axis_tick", label="B", bbox=(110.0, 505.0, 190.0, 535.0),
                font_px=14.0, is_queried_text=True,
            ),
        ]
    )
    rep = validate_task(bad, fam, img_path)
    assert not rep.valid
    assert any("overlap" in r.lower() for r in rep.rejection_reasons)
