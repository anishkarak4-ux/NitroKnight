"""Deterministic real-world scan/camera perturbation suite for VLM robustness testing."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance

from vtf.factory import TaskFactory
from vtf.families import get_family
from vtf.schema import SceneElement, SceneManifest, TaskPackage
from vtf.validator import validate_task

PERTURBATION_MODES = ("clean", "scan_tilt", "low_contrast_jpeg")


def _rotate_bbox(
    bbox: tuple[float, float, float, float],
    angle_deg: float,
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    """Transform an axis-aligned bbox after PIL.Image.rotate(angle_deg) around canvas center."""
    cx, cy = width / 2.0, height / 2.0
    # PIL rotates counter-clockwise in standard top-left screen coordinates -> negate angle
    rad = -math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    x0, y0, x1, y1 = bbox
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    xs: list[float] = []
    ys: list[float] = []
    for px, py in corners:
        dx, dy = px - cx, py - cy
        nx = cx + dx * ca - dy * sa
        ny = cy + dx * sa + dy * ca
        xs.append(min(float(width), max(0.0, nx)))
        ys.append(min(float(height), max(0.0, ny)))
    rx0, ry0, rx1, ry1 = min(xs), min(ys), max(xs), max(ys)
    if rx1 <= rx0:
        rx1 = min(float(width), rx0 + 1.0)
    if ry1 <= ry0:
        ry1 = min(float(height), ry0 + 1.0)
    return (round(rx0, 2), round(ry0, 2), round(rx1, 2), round(ry1, 2))


def apply_perturbation(
    image_path: Path,
    out_image_path: Path,
    manifest: SceneManifest,
    mode: str,
    seed: int,
) -> SceneManifest:
    """Apply deterministic visual perturbation while updating SceneManifest coordinates."""
    if mode not in PERTURBATION_MODES:
        raise ValueError(f"Unsupported perturbation mode '{mode}'. Choose from {PERTURBATION_MODES}.")

    out_image_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as im:
        rgb = im.convert("RGB")

    new_elements = [el.model_copy(deep=True) for el in manifest.elements]
    notes = list(manifest.notes)

    if mode == "clean":
        rgb.save(out_image_path, format="PNG")
        return SceneManifest(width=manifest.width, height=manifest.height, elements=new_elements, notes=notes)

    if mode == "scan_tilt":
        rng = np.random.default_rng(seed)
        angle = float(rng.choice([-2.2, -1.8, 1.8, 2.2]))
        tilted = rgb.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=(249, 248, 243),
        )
        # Subtle scanner JPEG quantization pass
        tmp_jpg = out_image_path.with_suffix(".tmp.jpg")
        try:
            tilted.save(tmp_jpg, format="JPEG", quality=76)
            with Image.open(tmp_jpg) as degraded:
                degraded.convert("RGB").save(out_image_path, format="PNG")
        finally:
            tmp_jpg.unlink(missing_ok=True)

        new_elements = [
            SceneElement(
                **{
                    **el.model_dump(),
                    "bbox": _rotate_bbox(el.bbox, angle, manifest.width, manifest.height),
                }
            )
            for el in new_elements
        ]
        notes.append(f"perturbation=scan_tilt(angle={angle:.1f}deg,jpg=76)")
        return SceneManifest(width=manifest.width, height=manifest.height, elements=new_elements, notes=notes)

    # low_contrast_jpeg
    rng = np.random.default_rng(seed + 101)
    faded = ImageEnhance.Contrast(rgb).enhance(0.74)
    arr = np.asarray(faded, dtype=np.float32)
    noise = rng.normal(0.0, 5.5, size=arr.shape).astype(np.float32)
    noisy = Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8), mode="RGB")
    tmp_jpg = out_image_path.with_suffix(".tmp.jpg")
    try:
        noisy.save(tmp_jpg, format="JPEG", quality=38)
        with Image.open(tmp_jpg) as degraded:
            degraded.convert("RGB").save(out_image_path, format="PNG")
    finally:
        tmp_jpg.unlink(missing_ok=True)
    notes.append("perturbation=low_contrast_jpeg(contrast=0.74,sigma=5.5,jpg=38)")
    return SceneManifest(width=manifest.width, height=manifest.height, elements=new_elements, notes=notes)


def perturb_dataset(
    dataset_dir: Path | str,
    out_dir: Path | str,
    mode: str = "scan_tilt",
    limit: int | None = None,
) -> dict[str, Any]:
    """Clone a validated dataset under deterministic real-world image perturbations."""
    src_dir = Path(dataset_dir)
    dst_dir = Path(out_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_img_dir = dst_dir / "images"
    dst_img_dir.mkdir(parents=True, exist_ok=True)

    tasks = TaskFactory.load_tasks(src_dir)
    if limit is not None:
        tasks = tasks[:limit]

    perturbed_tasks: list[TaskPackage] = []
    valid_count = 0
    for t in tasks:
        src_img = src_dir / t.image_path
        dst_img = dst_dir / t.image_path
        new_manifest = apply_perturbation(src_img, dst_img, t.manifest, mode=mode, seed=t.seed)
        sha = hashlib.sha256(dst_img.read_bytes()).hexdigest()
        pt = t.model_copy(
            deep=True,
            update={
                "image_sha256": sha,
                "manifest": new_manifest,
                "metadata": {**t.metadata, "perturbation_mode": mode, "source_dataset": str(src_dir)},
            },
        )
        pt.validation = validate_task(pt, get_family(pt.family), dst_img)
        if pt.validation.valid:
            valid_count += 1
        perturbed_tasks.append(pt)

    tasks_file = dst_dir / "tasks.jsonl"
    with tasks_file.open("w", encoding="utf-8") as f:
        for pt in perturbed_tasks:
            f.write(pt.model_dump_json() + "\n")

    summary = {
        "source_dataset": str(src_dir),
        "output_dir": str(dst_dir),
        "perturbation_mode": mode,
        "total_tasks": len(perturbed_tasks),
        "valid_tasks": valid_count,
    }
    (dst_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
