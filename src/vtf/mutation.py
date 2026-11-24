"""Mutation testing suite proving the 5-gate validator and scorer catch injected faults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from vtf.factory import TaskFactory
from vtf.families import get_family
from vtf.schema import AnswerType, Difficulty, FamilyName, SceneElement
from vtf.scoring import verify_prediction
from vtf.validator import validate_task


def run_mutation_suite(work_dir: Path | str = "outputs/mutation_tmp") -> dict[str, Any]:
    """Inject deliberate faults into valid tasks/scorers and verify 100% kill rate."""
    tmp = Path(work_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    factory = TaskFactory(tmp)

    chart_task, _ = factory.generate_one(FamilyName.CHARTS, Difficulty.EASY, seed=101)
    spatial_task, _ = factory.generate_one(FamilyName.SPATIAL_INVENTORY, Difficulty.EASY, seed=202)
    doc_task, _ = factory.generate_one(FamilyName.STRUCTURED_DOCS, Difficulty.MEDIUM, seed=303)

    chart_fam = get_family(FamilyName.CHARTS)
    spatial_fam = get_family(FamilyName.SPATIAL_INVENTORY)
    doc_fam = get_family(FamilyName.STRUCTURED_DOCS)

    results: list[dict[str, Any]] = []

    def _record(name: str, expected_gate: str, killed: bool, detail: str) -> None:
        results.append(
            {
                "mutant": name,
                "expected_detector": expected_gate,
                "killed": killed,
                "detail": detail,
            }
        )

    # 1. Clipped out-of-bounds element
    m1 = spatial_task.model_copy(deep=True)
    m1.manifest.elements.append(
        SceneElement(id="bad_clip", kind="crate", bbox=(1050.0, 10.0, 1250.0, 90.0))
    )
    r1 = validate_task(m1, spatial_fam, tmp / spatial_task.image_path)
    _record("clipped_element_bbox", "image_integrity_and_bounds", not r1.valid, "; ".join(r1.rejection_reasons))

    # 2. Corrupted / mismatched image dimensions
    corrupt_img = tmp / "corrupt_dims.png"
    Image.new("RGB", (320, 200), "#FFFFFF").save(corrupt_img)
    r2 = validate_task(spatial_task, spatial_fam, corrupt_img)
    _record("mismatched_image_dimensions", "image_integrity_and_bounds", not r2.valid, "; ".join(r2.rejection_reasons))

    # 3. Overlapping queried tick labels
    m3 = chart_task.model_copy(deep=True)
    m3.manifest.elements.extend(
        [
            SceneElement(
                id="xtick_mutA", kind="axis_tick", label="A", bbox=(100.0, 500.0, 190.0, 530.0),
                font_px=14.0, is_queried_text=True,
            ),
            SceneElement(
                id="xtick_mutB", kind="axis_tick", label="B", bbox=(110.0, 505.0, 200.0, 535.0),
                font_px=14.0, is_queried_text=True,
            ),
        ]
    )
    r3 = validate_task(m3, chart_fam, tmp / chart_task.image_path)
    _record("overlapping_queried_labels", "visual_readability_and_overlap", not r3.valid, "; ".join(r3.rejection_reasons))

    # 4. Illegibly small font (<10px)
    m4 = doc_task.model_copy(deep=True)
    m4.manifest.elements.append(
        SceneElement(
            id="tiny_lbl", kind="value_label", label="x", bbox=(20.0, 20.0, 30.0, 28.0),
            font_px=6.5, is_queried_text=True,
        )
    )
    r4 = validate_task(m4, doc_fam, tmp / doc_task.image_path)
    _record("tiny_unreadable_font", "visual_readability_and_overlap", not r4.valid, "; ".join(r4.rejection_reasons))

    # 5. Ungrounded question reference (element missing from image)
    m5 = spatial_task.model_copy(deep=True)
    m5.referenced_ids.append("ghost_crate_99")
    r5 = validate_task(m5, spatial_fam, tmp / spatial_task.image_path)
    _record("ungrounded_question_entity", "strict_qa_grounding", not r5.valid, "; ".join(r5.rejection_reasons))

    # 6. Hidden / excessively occluded referenced element
    m6 = spatial_task.model_copy(deep=True)
    target_id = m6.referenced_ids[0]
    for el in m6.manifest.elements:
        if el.id == target_id:
            el.visible = False
    r6 = validate_task(m6, spatial_fam, tmp / spatial_task.image_path)
    _record("hidden_referenced_element", "strict_qa_grounding", not r6.valid, "; ".join(r6.rejection_reasons))

    # 7. Corrupted ground-truth answer (solver disagreement)
    m7 = doc_task.model_copy(deep=True)
    m7.answer = -999999
    r7 = validate_task(m7, doc_fam, tmp / doc_task.image_path)
    _record("corrupted_ground_truth_answer", "independent_solver_verification", not r7.valid, "; ".join(r7.rejection_reasons))

    # 8. Verbatim answer leakage inside question
    m8 = chart_task.model_copy(deep=True)
    m8.answer = "SecretLeakTarget"
    m8.answer_type = AnswerType.STRING
    m8.question = "Which category equals SecretLeakTarget in this chart?"
    r8 = validate_task(m8, chart_fam, tmp / chart_task.image_path)
    _record("verbatim_answer_leakage", "anti_shortcut_leakage_audit", not r8.valid, "; ".join(r8.rejection_reasons))

    # 9. Scorer detects deliberately wrong prediction
    _, ok_num, _, cat_num = verify_prediction('{"answer": 99999}', 42, AnswerType.INTEGER, tolerance=1.0)
    _record("scorer_rejects_wrong_numeric", "verify_prediction", not ok_num, f"error_category={cat_num}")

    killed_count = sum(1 for r in results if r["killed"])
    report = {
        "total_mutants": len(results),
        "killed_mutants": killed_count,
        "mutation_kill_rate": round(killed_count / len(results), 4),
        "all_killed": killed_count == len(results),
        "mutants": results,
    }
    return report


def save_mutation_report(out_path: Path | str, work_dir: Path | str = "outputs/mutation_tmp") -> dict[str, Any]:
    rep = run_mutation_suite(work_dir=work_dir)
    Path(out_path).write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return rep
