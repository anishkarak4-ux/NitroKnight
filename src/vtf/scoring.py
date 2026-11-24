"""Robust response parser and answer verification scorer."""

from __future__ import annotations

import json
import re
from typing import Any

from vtf.schema import AnswerType


def extract_answer_text(raw: str, answer_type: AnswerType) -> str:
    """Extract concise candidate answer from freeform or JSON model output."""
    text = (raw or "").strip()
    if not text:
        return ""

    # 1. JSON payload {"answer": ...}
    json_match = re.search(r"\{[^{}]*\"answer\"\s*:\s*([^}]+)\}", text, flags=re.IGNORECASE | re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if "answer" in parsed:
                return str(parsed["answer"]).strip()
        except Exception:
            pass

    # 2. Explicit tag or prefix
    for pat in (
        r"<answer>\s*(.*?)\s*</answer>",
        r"(?:final\s+answer|answer)\s*[:\-]\s*(.+)",
    ):
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().splitlines()[0].strip(" .\"'*`")
            if candidate:
                text = candidate
                break

    if answer_type in {AnswerType.INTEGER, AnswerType.NUMBER}:
        cleaned = text.replace(",", "")
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", cleaned)
        if nums:
            return nums[-1]

    if answer_type == AnswerType.BOOLEAN:
        low = text.lower()
        if any(tok in low for tok in ("true", "yes")):
            return "true"
        if any(tok in low for tok in ("false", "no")):
            return "false"

    # Strip markdown emphasis & trailing punctuation
    return text.strip(" .\"'*`\n\r\t")


def verify_prediction(
    raw_response: str,
    expected: Any,
    answer_type: AnswerType,
    tolerance: float = 0.0,
) -> tuple[str, bool, float, str | None]:
    """Compare extracted model response against verified ground truth.

    Returns:
        (extracted_answer, is_correct, score, error_category)
    """
    extracted = extract_answer_text(raw_response, answer_type)
    if not extracted:
        return "", False, 0.0, "parse_failure"

    if answer_type == AnswerType.INTEGER:
        try:
            pred_val = float(extracted)
            exp_val = float(expected)
            if abs(pred_val - exp_val) <= max(1e-6, tolerance):
                return str(int(round(pred_val))) if pred_val.is_integer() else str(pred_val), True, 1.0, None
            return extracted, False, 0.0, "numeric_mismatch"
        except ValueError:
            return extracted, False, 0.0, "parse_failure"

    if answer_type == AnswerType.NUMBER:
        try:
            pred_val = float(extracted)
            exp_val = float(expected)
            if abs(pred_val - exp_val) <= max(1e-4, tolerance):
                return extracted, True, 1.0, None
            return extracted, False, 0.0, "numeric_mismatch"
        except ValueError:
            return extracted, False, 0.0, "parse_failure"

    if answer_type == AnswerType.BOOLEAN:
        exp_norm = "true" if str(expected).lower() in {"true", "yes", "1"} else "false"
        pred_norm = "true" if extracted.lower() in {"true", "yes", "1"} else (
            "false" if extracted.lower() in {"false", "no", "0"} else extracted.lower()
        )
        ok = pred_norm == exp_norm
        return pred_norm, ok, 1.0 if ok else 0.0, None if ok else "boolean_mismatch"

    # STRING normalization: case-insensitive, whitespace-collapsed, strip currency/punctuation
    norm_pred = _norm_str(extracted)
    norm_exp = _norm_str(str(expected))
    if norm_pred == norm_exp:
        return extracted, True, 1.0, None

    # Allow clean containment only if response is concise (e.g. "SKU-204 ($42)" -> "SKU-204")
    if norm_exp in norm_pred and len(norm_pred) <= len(norm_exp) + 12:
        return extracted, True, 1.0, None

    return extracted, False, 0.0, "wrong_entity"


def _norm_str(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[\"'`$]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,:;")
