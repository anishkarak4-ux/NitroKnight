"""Canonical Pydantic schemas for the Visual Task Factory."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class FamilyName(str, Enum):
    CHARTS = "charts"
    SPATIAL_INVENTORY = "spatial_inventory"
    LOGIC_CIRCUITS = "logic_circuits"
    STRUCTURED_DOCS = "structured_docs"


class AnswerType(str, Enum):
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"


class SceneElement(BaseModel):
    """Rendered visual primitive with pixel bounding box for grounding checks."""

    id: str
    kind: str
    label: str = ""
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1) top-left origin
    visible: bool = True
    occluded_fraction: float = 0.0
    font_px: float | None = None
    is_queried_text: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class SceneManifest(BaseModel):
    """Full visual layout inventory of a rendered image."""

    width: int
    height: int
    elements: list[SceneElement] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def by_id(self) -> dict[str, SceneElement]:
        return {el.id: el for el in self.elements}


class ValidationGateResult(BaseModel):
    """Outcome of a single automated validation gate."""

    gate_name: str
    passed: bool
    severity: str = "error"  # "error" or "warning"
    details: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Aggregate validation result proving visual and logical task validity."""

    valid: bool
    gates: list[ValidationGateResult] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    grounding_coverage: float = 0.0
    shortcut_risk: float = 0.0
    blind_guess_answer: str | None = None


class TaskPackage(BaseModel):
    """Complete self-contained visual task artifact produced by the factory."""

    task_id: str
    seed: int
    family: FamilyName
    subtype: str
    difficulty: Difficulty
    reasoning_type: str
    image_path: str
    image_sha256: str
    question: str
    answer: Any
    answer_type: AnswerType
    tolerance: float = 0.0
    unit: str = ""
    referenced_ids: list[str] = Field(default_factory=list)
    answer_evidence_ids: list[str] = Field(default_factory=list)
    ground_truth_spec: dict[str, Any] = Field(default_factory=dict)
    solver_trace: list[str] = Field(default_factory=list)
    manifest: SceneManifest
    validation: ValidationReport | None = None
    counterfactual_of: str | None = None
    counterfactual_delta: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelPrediction(BaseModel):
    """Single model response and verification score for one task."""

    task_id: str
    model_name: str
    provider: str
    raw_response: str
    extracted_answer: str
    expected_answer: str
    correct: bool
    score: float  # 0.0 to 1.0
    error_category: str | None = None
    latency_ms: float = 0.0
    used_image: bool = True
    notes: str = ""


class CounterfactualPairMetrics(BaseModel):
    """Tracks whether a model actually used pixels across a minimal visual pair."""

    base_task_id: str
    twin_task_id: str
    model_name: str
    base_correct: bool
    twin_correct: bool
    prediction_changed: bool
    consistently_visual: bool


class BenchmarkSummary(BaseModel):
    """Aggregated evaluation report across models, families, and difficulties."""

    dataset_dir: str
    total_tasks: int
    valid_tasks: int
    rejected_candidates: int = 0
    models_evaluated: list[str] = Field(default_factory=list)
    overall_accuracy: dict[str, float] = Field(default_factory=dict)
    by_family: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_difficulty: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_reasoning: dict[str, dict[str, float]] = Field(default_factory=dict)
    counterfactual_consistency: dict[str, float] = Field(default_factory=dict)
    predictions: list[ModelPrediction] = Field(default_factory=list)
    counterfactual_details: list[CounterfactualPairMetrics] = Field(default_factory=list)
