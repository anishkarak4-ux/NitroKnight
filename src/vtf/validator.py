"""Five-gate automated task validator verifying grounding, readability, and non-triviality."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PIL import Image

from vtf.families.base import VisualTaskFamily
from vtf.schema import (
    AnswerType,
    TaskPackage,
    ValidationGateResult,
    ValidationReport,
)


def _bbox_intersection_ratio(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> float:
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(1.0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / min(area_a, area_b)


def validate_task(
    task: TaskPackage,
    family: VisualTaskFamily,
    image_path: Path,
) -> ValidationReport:
    """Run all 5 deterministic verification gates on a generated TaskPackage."""
    gates: list[ValidationGateResult] = []
    rejections: list[str] = []

    # ── Gate 1: Image Integrity & Canvas Bounds ───────────────────────────────
    g1_issues: list[str] = []
    if not image_path.exists():
        g1_issues.append(f"Missing image file: {image_path}")
    else:
        with Image.open(image_path) as im:
            im_w, im_h = im.size
        if (im_w, im_h) != (task.manifest.width, task.manifest.height):
            g1_issues.append(
                f"Image dims ({im_w}x{im_h}) != manifest dims ({task.manifest.width}x{task.manifest.height})"
            )
        for el in task.manifest.elements:
            x0, y0, x1, y1 = el.bbox
            if x1 <= x0 or y1 <= y0:
                g1_issues.append(f"Degenerate bbox on {el.id}: {el.bbox}")
            if x0 < -2 or y0 < -2 or x1 > im_w + 2 or y1 > im_h + 2:
                g1_issues.append(f"Out-of-bounds element {el.id}: {el.bbox} outside {im_w}x{im_h}")

    g1_ok = len(g1_issues) == 0
    gates.append(
        ValidationGateResult(
            gate_name="image_integrity_and_bounds",
            passed=g1_ok,
            details="All elements within canvas bounds." if g1_ok else "; ".join(g1_issues[:3]),
            metrics={"element_count": len(task.manifest.elements), "issue_count": len(g1_issues)},
        )
    )
    if not g1_ok:
        rejections.extend(g1_issues)

    # ── Gate 2: Visual Readability & Anti-Overlap ─────────────────────────────
    g2_issues: list[str] = []
    queried_txt = [e for e in task.manifest.elements if e.is_queried_text]
    for el in queried_txt:
        if el.font_px is not None and el.font_px < 10.0:
            g2_issues.append(f"Font too small ({el.font_px:.1f}px) on {el.id}")

    # Check pairwise overlap between queried text elements (excluding parent row vs child or same kind tick check)
    text_elems = [e for e in queried_txt if e.kind in {"axis_tick", "value_label", "shelf_label", "edge", "logic_gate"}]
    max_text_overlap = 0.0
    for i in range(len(text_elems)):
        for j in range(i + 1, len(text_elems)):
            ratio = _bbox_intersection_ratio(text_elems[i].bbox, text_elems[j].bbox)
            if ratio > max_text_overlap:
                max_text_overlap = ratio
            if ratio > 0.12:
                g2_issues.append(
                    f"Text overlap {ratio:.2f} between {text_elems[i].id} and {text_elems[j].id}"
                )

    # For occlusion tasks, verify the occluded object actually has partial (not zero/total) occlusion
    if task.reasoning_type == "occlusion_depth_ordering":
        back_id = task.ground_truth_spec.get("back_id")
        front_id = task.ground_truth_spec.get("front_id")
        el_map = task.manifest.by_id()
        back_el = el_map.get(str(back_id))
        front_el = el_map.get(str(front_id))
        if not back_el or not front_el:
            g2_issues.append("Missing occlusion target elements in manifest.")
        else:
            occ = max(back_el.occluded_fraction, front_el.occluded_fraction)
            if occ < 0.05 or occ > 0.72:
                g2_issues.append(f"Invalid occlusion fraction {occ:.3f}; expected [0.05, 0.72].")

    g2_ok = len(g2_issues) == 0
    gates.append(
        ValidationGateResult(
            gate_name="visual_readability_and_overlap",
            passed=g2_ok,
            details="No illegible fonts or colliding labels." if g2_ok else "; ".join(g2_issues[:3]),
            metrics={"max_text_overlap": round(max_text_overlap, 3), "queried_text_count": len(queried_txt)},
        )
    )
    if not g2_ok:
        rejections.extend(g2_issues)

    # ── Gate 3: Strict Question & Answer Grounding (Klent's Golden Rule) ──────
    el_map = task.manifest.by_id()
    missing_refs = [rid for rid in task.referenced_ids if rid not in el_map]
    hidden_refs = [
        rid
        for rid in task.referenced_ids
        if rid in el_map and (not el_map[rid].visible or el_map[rid].occluded_fraction >= 0.75)
    ]
    missing_ev = [eid for eid in task.answer_evidence_ids if eid not in el_map]
    ref_total = max(1, len(task.referenced_ids))
    grounding_cov = (len(task.referenced_ids) - len(missing_refs) - len(hidden_refs)) / ref_total

    g3_issues: list[str] = []
    if not task.referenced_ids:
        g3_issues.append("Task has empty referenced_ids.")
    if missing_refs:
        g3_issues.append(f"Question references elements absent from image: {missing_refs[:3]}")
    if hidden_refs:
        g3_issues.append(f"Referenced elements are hidden/excessively occluded: {hidden_refs[:3]}")
    if missing_ev:
        g3_issues.append(f"Answer evidence elements absent from image: {missing_ev[:3]}")

    g3_ok = len(g3_issues) == 0
    gates.append(
        ValidationGateResult(
            gate_name="strict_qa_grounding",
            passed=g3_ok,
            details=(
                f"100% of {len(task.referenced_ids)} referenced primitives visibly grounded."
                if g3_ok
                else "; ".join(g3_issues)
            ),
            metrics={
                "grounding_coverage": round(grounding_cov, 3),
                "referenced_count": len(task.referenced_ids),
                "evidence_count": len(task.answer_evidence_ids),
            },
        )
    )
    if not g3_ok:
        rejections.extend(g3_issues)

    # ── Gate 4: Independent Symbolic Solver Cross-Check ───────────────────────
    (
        re_ans,
        re_type,
        re_tol,
        _unit,
        _refs,
        _evs,
        re_trace,
    ) = family.solve_spec(task.ground_truth_spec)
    g4_ok = (
        str(re_ans) == str(task.answer)
        and re_type == task.answer_type
        and abs(re_tol - task.tolerance) < 1e-6
        and len(re_trace) > 0
    )
    gates.append(
        ValidationGateResult(
            gate_name="independent_solver_verification",
            passed=g4_ok,
            details="Independent spec re-derivation matches ground truth." if g4_ok else "Solver mismatch!",
            metrics={"solver_steps": len(re_trace)},
        )
    )
    if not g4_ok:
        rejections.append("Independent solver cross-check disagreed with stored task answer.")

    # ── Gate 5: Anti-Shortcut & Answer-Leakage Audit ──────────────────────────
    shortcut_risk, blind_guess, leak_issue = _estimate_shortcut_risk(task)
    g5_ok = leak_issue is None
    gates.append(
        ValidationGateResult(
            gate_name="anti_shortcut_leakage_audit",
            passed=g5_ok,
            details="No verbatim answer leakage; requires visual inspection." if g5_ok else leak_issue,
            metrics={"shortcut_risk": round(shortcut_risk, 3), "blind_guess_prior": blind_guess},
        )
    )
    if not g5_ok and leak_issue:
        rejections.append(leak_issue)

    return ValidationReport(
        valid=len(rejections) == 0,
        gates=gates,
        rejection_reasons=rejections,
        grounding_coverage=round(grounding_cov, 3),
        shortcut_risk=round(shortcut_risk, 3),
        blind_guess_answer=blind_guess,
    )


def _estimate_shortcut_risk(task: TaskPackage) -> tuple[float, str | None, str | None]:
    """Check whether answer leaks directly in question text or is heavily prior-biased."""
    q_low = task.question.lower()
    ans_str = str(task.answer).strip()
    ans_low = ans_str.lower()

    # For categorical string answers not explicitly framed as a small choice set, verbatim presence is a leak
    if task.answer_type == AnswerType.STRING and len(ans_low) >= 3:
        # Allowed explicit choice lists in binary/4-way questions (e.g. "(Red vs Blue)" or "(A, B, C, or D)")
        in_parens = any(ans_low in grp.lower() for grp in re.findall(r"\(([^)]+)\)", task.question))
        if not in_parens and re.search(rf"\b{re.escape(ans_low)}\b", q_low):
            return 1.0, ans_str, f"Answer '{ans_str}' leaked verbatim inside question text."

    # Estimate blind random-guess prior probability
    if task.reasoning_type == "occlusion_depth_ordering":
        m = re.search(r"\(([^)]+)\s+vs\s+([^)]+)\)", task.question, flags=re.IGNORECASE)
        guess = m.group(1).strip() if m else None
        return 0.5, guess, None
    if task.reasoning_type == "circuit_signal_tracing":
        return 0.5, "0", None
    if task.reasoning_type == "circuit_fault_sensitivity":
        return 0.25, "A", None
    if task.answer_type == AnswerType.STRING:
        return 0.18, None, None
    return 0.08, None, None
