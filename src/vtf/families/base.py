"""Base interfaces and shared geometry/hashing helpers for visual task families."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from PIL import ImageDraw, ImageFont

from vtf.schema import AnswerType, Difficulty, FamilyName, SceneManifest, TaskPackage


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    anchor: str = "la",
) -> tuple[float, float, float, float]:
    """Return (x0, y0, x1, y1) bounding box for Pillow drawn text."""
    left, top, right, bottom = draw.textbbox(xy, text, font=font, anchor=anchor)
    return (float(left), float(top), float(right), float(bottom))


class VisualTaskFamily(ABC):
    """Abstract factory interface implemented by every visual task domain."""

    family_name: FamilyName

    @abstractmethod
    def generate_spec(self, seed: int, difficulty: Difficulty) -> dict[str, Any]:
        """Deterministically produce a ground-truth scene/task specification."""

    @abstractmethod
    def render_spec(self, spec: dict[str, Any], out_path: Path) -> SceneManifest:
        """Render the spec into a PNG image and return exact pixel bounding boxes."""

    @abstractmethod
    def solve_spec(
        self, spec: dict[str, Any]
    ) -> tuple[Any, AnswerType, float, str, list[str], list[str], list[str]]:
        """Independently compute the verified answer and grounding IDs from spec.

        Returns:
            (answer, answer_type, tolerance, unit, referenced_ids, answer_evidence_ids, solver_trace)
        """

    @abstractmethod
    def make_counterfactual_spec(
        self, spec: dict[str, Any], seed: int
    ) -> tuple[dict[str, Any], str] | None:
        """Produce a minimally modified twin spec whose verified answer flips."""

    def build_task(
        self,
        seed: int,
        difficulty: Difficulty,
        images_dir: Path,
        *,
        task_id: str | None = None,
        spec_override: dict[str, Any] | None = None,
        counterfactual_of: str | None = None,
        counterfactual_delta: str | None = None,
    ) -> TaskPackage:
        """Generate image, manifest, exact solution, and TaskPackage."""
        spec = spec_override if spec_override is not None else self.generate_spec(seed, difficulty)
        tid = task_id or f"{self.family_name.value}_{difficulty.value}_s{seed}"
        images_dir.mkdir(parents=True, exist_ok=True)
        img_path = images_dir / f"{tid}.png"
        manifest = self.render_spec(spec, img_path)
        (
            answer,
            answer_type,
            tolerance,
            unit,
            referenced_ids,
            answer_evidence_ids,
            solver_trace,
        ) = self.solve_spec(spec)

        return TaskPackage(
            task_id=tid,
            seed=seed,
            family=self.family_name,
            subtype=str(spec["subtype"]),
            difficulty=difficulty,
            reasoning_type=str(spec["reasoning_type"]),
            image_path=f"images/{tid}.png",
            image_sha256=sha256_file(img_path),
            question=str(spec["question"]),
            answer=answer,
            answer_type=answer_type,
            tolerance=tolerance,
            unit=unit,
            referenced_ids=referenced_ids,
            answer_evidence_ids=answer_evidence_ids,
            ground_truth_spec=spec,
            solver_trace=solver_trace,
            manifest=manifest,
            counterfactual_of=counterfactual_of,
            counterfactual_delta=counterfactual_delta,
            metadata={"theme": spec.get("theme_name", "default")},
        )
