"""Generates high-resolution architecture, sample-collage, and validation visuals for slides."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

from vtf.fonts import get_font
from vtf.schema import BenchmarkSummary


def generate_slide_assets(
    samples_dir: Path | str = "samples/demo_suite",
    assets_dir: Path | str = "docs/assets",
    summary: BenchmarkSummary | None = None,
) -> list[Path]:
    out = Path(assets_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    arch_path = out / "architecture_diagram.png"
    _draw_architecture_diagram(arch_path)
    generated.append(arch_path)

    collage_path = out / "families_showcase.png"
    if _draw_families_collage(Path(samples_dir) / "images", collage_path):
        generated.append(collage_path)

    if summary is not None:
        bench_path = out / "validation_and_baselines.png"
        _draw_baseline_chart(summary, bench_path)
        generated.append(bench_path)

        fam_path = out / "model_failure_breakdown.png"
        _draw_family_breakdown_chart(summary, fam_path)
        generated.append(fam_path)

    return generated


def _draw_architecture_diagram(out_path: Path) -> None:
    w, h = 1400, 720
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)
    title_font = get_font(26, bold=True)
    box_title = get_font(17, bold=True)
    box_sub = get_font(13, bold=False)

    draw.text(
        (50, 28),
        "Visual Task Factory — Spec-First Deterministic Synthesis & Evaluation Pipeline",
        fill="#0F172A",
        font=title_font,
    )

    def box(x0: int, y0: int, x1: int, y1: int, fill: str, edge: str, title: str, lines: list[str]) -> None:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=fill, outline=edge, width=3)
        draw.text(((x0 + x1) / 2, y0 + 28), title, fill="#0F172A", font=box_title, anchor="mm")
        for idx, ln in enumerate(lines):
            draw.text(((x0 + x1) / 2, y0 + 58 + idx * 21), ln, fill="#334155", font=box_sub, anchor="mm")

    def arrow(p0: tuple[int, int], p1: tuple[int, int], color: str = "#334155") -> None:
        draw.line([p0, p1], fill=color, width=4)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        if abs(dx) >= abs(dy):
            sgn = 1 if dx > 0 else -1
            draw.polygon([(p1[0], p1[1]), (p1[0] - 12 * sgn, p1[1] - 7), (p1[0] - 12 * sgn, p1[1] + 7)], fill=color)
        else:
            sgn = 1 if dy > 0 else -1
            draw.polygon([(p1[0], p1[1]), (p1[0] - 7, p1[1] - 12 * sgn), (p1[0] + 7, p1[1] - 12 * sgn)], fill=color)

    # Row 1: Spec -> Renderer + Symbolic Solver -> 5-Gate Validator
    box(50, 110, 310, 270, "#DBEAFE", "#2563EB", "1. Seeded Spec Generator", [
        "Seed + Family + Difficulty",
        "4 Families: Charts, Spatial,",
        "Logic Circuits, Invoices/QA",
        "Canonical JSON World Spec",
    ])
    box(380, 90, 670, 210, "#ECFDF5", "#059669", "2a. Deterministic Renderer", [
        "Matplotlib / Pillow Synthesis",
        "PNG + Pixel SceneManifest",
        "Exact BBoxes & Occlusion %",
    ])
    box(380, 235, 670, 355, "#FEF3C7", "#D97706", "2b. Exact Symbolic Solver", [
        "Direct Ground-Truth Compute",
        "Step-by-step solver_trace",
        "Referenced & Evidence IDs",
    ])
    box(740, 110, 1060, 330, "#F3E8FF", "#7C3AED", "3. 5-Gate Automated Validator", [
        "G1: Bounds & Image Integrity",
        "G2: Readability & Zero Overlap",
        "G3: Strict Q/A Visual Grounding",
        "G4: Independent Solver Check",
        "G5: Anti-Shortcut Leakage Audit",
        "-> 9/9 Mutation Kill Rate",
    ])
    box(1120, 130, 1350, 305, "#DCFCE7", "#16A34A", "4. Validated TaskPkg", [
        "Base Task + PNG + JSON",
        "+ Counterfactual Twin (*_cf)",
        "Flips Answer via 1 Visual Edit",
    ])

    arrow((310, 160), (380, 150))
    arrow((310, 230), (380, 290))
    arrow((670, 150), (740, 180))
    arrow((670, 290), (740, 255))
    arrow((1060, 220), (1120, 220))

    # Row 2: Evaluation Harness & Studio
    box(180, 450, 560, 635, "#E0F2FE", "#0284C7", "5. Pluggable Multimodal Evaluator", [
        "Real VLMs: Gemini Flash, OpenAI/OpenRouter,",
        "Local Ollama Vision (qwen2.5vl / moondream)",
        "Baselines: blind_text_prior (8.3%) & pixel_cv (12.5%)",
        "Oracle: oracle_spec_verifier (100.0%)",
    ])
    box(630, 450, 1000, 635, "#FFE4E6", "#E11D48", "6. Diagnostic & Consistency Analytics", [
        "Accuracy by Family x Difficulty x Reasoning",
        "Counterfactual Visual Consistency Metric",
        "Auto-generated Markdown/JSON Reports",
        "Failure Mode Taxonomy Exposure",
    ])
    box(1060, 450, 1350, 635, "#F1F5F9", "#334155", "7. Interactive Studio UI", [
        "FastAPI + CLI (vtf serve)",
        "Live Generation & Validation",
        "SVG Grounding Box Overlay",
        "Dockerized Judge Execution",
    ])

    arrow((1235, 305), (1235, 390))
    draw.line([(1235, 390), (370, 390)], fill="#334155", width=4)
    arrow((370, 390), (370, 450))
    arrow((560, 542), (630, 542))
    arrow((1000, 542), (1060, 542))

    img.save(out_path)


def _draw_families_collage(images_dir: Path, out_path: Path) -> bool:
    picks = [
        ("charts", "1. Analytics Charts (Dual-Axis / Grouped / Stacked)"),
        ("spatial_inventory", "2. Spatial Inventory & CLEVR Occlusion"),
        ("logic_circuits", "3. Logic Schematics & Flow Networks"),
        ("structured_docs", "4. Enterprise Invoices & QA Matrices"),
    ]
    chosen: list[tuple[str, Path]] = []
    for prefix, label in picks:
        matches = sorted(p for p in images_dir.glob(f"{prefix}_*.png") if not p.name.endswith("_cf.png"))
        if not matches:
            return False
        # Prefer medium/hard non-cf sample for visual richness
        preferred = [p for p in matches if "_hard_" in p.name or "_medium_" in p.name]
        chosen.append((label, preferred[-1] if preferred else matches[0]))

    cw, ch = 640, 410
    pad = 24
    canvas = Image.new("RGB", (cw * 2 + pad * 3, ch * 2 + pad * 3 + 50), "#F8FAFC")
    draw = ImageDraw.Draw(canvas)
    h_font = get_font(24, bold=True)
    cap_font = get_font(15, bold=True)
    draw.text((pad, 16), "Meaningful Variation: 4 Distinct Visual Families (Sample Outputs)", fill="#0F172A", font=h_font)

    for idx, (label, path) in enumerate(chosen):
        r, c = divmod(idx, 2)
        x0 = pad + c * (cw + pad)
        y0 = 60 + pad + r * (ch + pad)
        draw.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=10, fill="#FFFFFF", outline="#CBD5E1", width=2)
        draw.text((x0 + 14, y0 + 10), label, fill="#1E293B", font=cap_font)
        with Image.open(path) as im:
            thumb = im.convert("RGB").resize((cw - 20, ch - 46), Image.Resampling.LANCZOS)
            canvas.paste(thumb, (x0 + 10, y0 + 38))

    canvas.save(out_path)
    return True


def _draw_baseline_chart(summary: BenchmarkSummary, out_path: Path) -> None:
    models = summary.models_evaluated
    acc = [summary.overall_accuracy.get(m, 0.0) * 100 for m in models]
    cf = [summary.counterfactual_consistency.get(m, 0.0) * 100 for m in models]

    x = np.arange(len(models))
    width = 0.34
    fig_w = max(9.2, 2.2 * len(models))
    fig, ax = plt.subplots(figsize=(fig_w, 5.2), dpi=130)
    try:
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F8FAFC")
        b1 = ax.bar(x - width / 2, acc, width, label="Overall Accuracy (%)", color="#2563EB", zorder=3)
        b2 = ax.bar(x + width / 2, cf, width, label="Counterfactual Consistency (%)", color="#0D9488", zorder=3)
        ax.set_ylim(0, 118)
        ax.set_ylabel("Score (%)")
        ax.set_title("Model Benchmarking, Anti-Shortcut Verification & Consistency", fontsize=13, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(models, fontsize=9.5, rotation=12 if len(models) > 3 else 0)
        ax.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for bars in (b1, b2):
            for bar in bars:
                v = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, v + 2, f"{v:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.legend(loc="upper left", frameon=True)
        fig.tight_layout()
        fig.savefig(out_path, dpi=130)
    finally:
        plt.close(fig)


def _draw_family_breakdown_chart(summary: BenchmarkSummary, out_path: Path) -> None:
    """Plot accuracy across all 4 visual families for evaluated models (excluding oracle)."""
    models = [m for m in summary.models_evaluated if m != "oracle_spec_verifier"]
    if not models:
        models = list(summary.models_evaluated)
    families = ["charts", "spatial_inventory", "logic_circuits", "structured_docs"]
    fam_labels = ["Charts", "Spatial / Occlusion", "Logic & Flow", "Invoices & QA"]
    palette = ["#64748B", "#94A3B8", "#0EA5E9", "#2563EB", "#7C3AED", "#0D9488"]

    x = np.arange(len(families))
    n = len(models)
    width = min(0.22, 0.78 / max(1, n))

    fig, ax = plt.subplots(figsize=(10.4, 5.2), dpi=130)
    try:
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F8FAFC")
        for idx, m in enumerate(models):
            vals = [summary.by_family.get(m, {}).get(f, 0.0) * 100 for f in families]
            offset = (idx - (n - 1) / 2.0) * width
            bars = ax.bar(x + offset, vals, width, label=m, color=palette[idx % len(palette)], zorder=3)
            for b in bars:
                v = b.get_height()
                ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
        ax.set_ylim(0, 118)
        ax.set_ylabel("Accuracy (%)")
        ax.set_title("Where Multimodal Models Succeed vs Struggle (Accuracy by Visual Family)", fontsize=12.5, fontweight="bold", pad=28)
        ax.set_xticks(x)
        ax.set_xticklabels(fam_labels, fontsize=10)
        ax.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, 1.01),
            ncol=min(4, len(models)),
            fontsize=8.5,
            frameon=True,
        )
        fig.tight_layout()
        fig.savefig(out_path, dpi=130)
    finally:
        plt.close(fig)
