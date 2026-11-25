"""Unit tests for response extraction and answer verification."""

from vtf.schema import AnswerType
from vtf.scoring import verify_prediction


def test_json_and_freeform_numeric_extraction() -> None:
    _, ok, _, _ = verify_prediction('{"answer": 42, "reason": "84 - 42"}', 42, AnswerType.INTEGER)
    assert ok

    _, ok, _, _ = verify_prediction("Final Answer: $1,250", 1250, AnswerType.INTEGER)
    assert ok

    _, ok, _, _ = verify_prediction("About 47 units", 49, AnswerType.INTEGER, tolerance=3.0)
    assert ok

    _, ok, _, cat = verify_prediction("About 40 units", 49, AnswerType.INTEGER, tolerance=3.0)
    assert not ok
    assert cat == "numeric_mismatch"


def test_string_and_boolean_normalization() -> None:
    _, ok, _, _ = verify_prediction('{"answer": "  analytics  "}', "Analytics", AnswerType.STRING)
    assert ok

    _, ok, _, _ = verify_prediction("<answer>SKU-204</answer>", "SKU-204", AnswerType.STRING)
    assert ok

    _, ok, _, _ = verify_prediction("Yes", True, AnswerType.BOOLEAN)
    assert ok

    _, ok, _, _ = verify_prediction('{"answer": "CANNOT_DETERMINE"}', "CANNOT_DETERMINE", AnswerType.STRING)
    assert ok
    _, ok_hal, _, _ = verify_prediction('{"answer": "$48"}', "CANNOT_DETERMINE", AnswerType.STRING)
    assert not ok_hal
