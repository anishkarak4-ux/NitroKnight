"""Generates high-resolution architecture, 5-family collage, validation, and failure visuals."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

from vtf.fonts import get_font
from vtf.schema import BenchmarkSummary, TaskPackage


def generate_slide_assets(
    samples_dir: Path | str = "samples/demo_suite",
    assets_dir: Path | str = "docs/assets",
    summary: BenchmarkSummary | None = None,
    tasks: list[TaskPackage] | None = None,
) -> list[Path]:
    out = Path(assets_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    arch_path = out / "architecture_diagram.png"
    _draw_architecture_diagram(arch_path, summary)
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

        if tasks:
            spot_path = out / "failure_spotlight.png"
            if _draw_failure_spotlight(Path(samples_dir), summary, tasks, spot_path):
                generated.append(spot_path)

    return generated


def _draw_architecture_diagram(out_path: Path, summary: BenchmarkSummary | None = None) -> None:
    w, h = 1400, 720
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)
    title_font = get_font(25, bold=True)
    box_title = get_font(17, bold=True)
    box_sub = get_font(13, bold=False)

    draw.text(
        (50, 26),
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

    blind_acc = f"{summary.overall_accuracy.get('blind_text_prior', 0.083)*100:.1f}%" if summary else "low"
    box(50, 110, 310, 275, "#DBEAFE", "#2563EB", "1. Seeded Spec Generator", [
        "Seed + Family + Difficulty",
        "5 Families: Charts, Spatial,",
        "Circuits, Docs & Blueprints",
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
    box(740, 105, 1060, 340, "#F3E8FF", "#7C3AED", "3. 5-Gate + Blind LLM Validator", [
        "G1: Bounds & Image Integrity",
        "G2: Readability & Zero Overlap",
        "G3: Strict Q/A Visual Grounding",
        "G4: Independent Solver Check",
        "G5: Anti-Shortcut + Mistral Audit",
        "-> 9/9 Mutation Kill Rate",
    ])
    box(1120, 130, 1350, 310, "#DCFCE7", "#16A34A", "4. Validated TaskPkg", [
        "Base Task + PNG + JSON",
        "+ Counterfactual Twin (*_cf)",
        "+ Redacted Abstention Tests",
    ])

    arrow((310, 160), (380, 150))
    arrow((310, 230), (380, 290))
    arrow((670, 150), (740, 180))
    arrow((670, 290), (740, 255))
    arrow((1060, 220), (1120, 220))

    box(150, 450, 560, 640, "#E0F2FE", "#0284C7", "5. Resumable VLM Evaluator", [
        "Real VLMs: Gemini Flash & Lite Variants,",
        "OpenAI/OpenRouter, Local Ollama Vision",
        f"Blind Audits: Regex ({blind_acc}) + Mistral LLM",
        "Oracle Verifier (100%) + JSONL Cache",
    ])
    box(610, 450, 1000, 640, "#FFE4E6", "#E11D48", "6. Diagnostic & Hallucination Reports", [
        "Accuracy by Family x Difficulty x Reasoning",
        "Counterfactual Visual Consistency Metric",
        "Hallucination Rate (Redacted Abstention)",
        "Standalone MD / JSON / HTML Reports",
    ])
    box(1050, 450, 1350, 640, "#F1F5F9", "#334155", "7. Studio UI 2.0 & CI", [
        "FastAPI + CLI (vtf serve / mutate)",
        "SVG Grounding Overlay + Twin Diff",
        "Failure Filter + Per-Model Logs",
        "Dockerfile + GitHub Actions CI",
    ])

    arrow((1235, 310), (1235, 390))
    draw.line([(1235, 390), (355, 390)], fill="#334155", width=4)
    arrow((355, 390), (355, 450))
    arrow((560, 545), (610, 545))
    arrow((1000, 545), (1050, 545))

    img.save(out_path)


def _draw_families_collage(images_dir: Path, out_path: Path) -> bool:
    picks = [
        ("charts", "1. Unlabeled & Analytical Charts"),
        ("spatial_inventory", "2. Warehouse & CLEVR Occlusion"),
        ("logic_circuits", "3. Crossing Logic & Flow DAGs"),
        ("structured_docs", "4. Invoices & Redacted Audits"),
        ("blueprints_gauges", "5. Blueprints & Analog Gauges"),
    ]
    chosen: list[tuple[str, Path]] = []
    for prefix, label in picks:
        matches = sorted(p for p in images_dir.glob(f"{prefix}_*.png") if not p.name.endswith("_cf.png"))
        if not matches:
            continue
        preferred = [p for p in matches if "_hard_" in p.name or "_medium_" in p.name]
        chosen.append((label, preferred[-1] if preferred else matches[0]))

    if not chosen:
        return False

    cw, ch = 440, 290
    pad = 18
    cols = 3
    rows = 2
    canvas = Image.new("RGB", (cw * cols + pad * (cols + 1), ch * rows + pad * (rows + 1) + 48), "#F8FAFC")
    draw = ImageDraw.Draw(canvas)
    h_font = get_font(22, bold=True)
    cap_font = get_font(13, bold=True)
    draw.text((pad, 14), "Meaningful Variation: 5 Distinct Visual Task Families", fill="#0F172A", font=h_font)

    for idx, (label, path) in enumerate(chosen):
        r, c = divmod(idx, cols)
        x0 = pad + c * (cw + pad)
        y0 = 52 + pad + r * (ch + pad)
        draw.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=10, fill="#FFFFFF", outline="#CBD5E1", width=2)
        draw.text((x0 + 12, y0 + 9), label, fill="#1E293B", font=cap_font)
        with Image.open(path) as im:
            im_rgb = im.convert("RGB")
            iw, ih = im_rgb.size
            max_tw, max_th = cw - 16, ch - 38
            scale = min(max_tw / iw, max_th / ih)
            nw, nh = max(1, int(round(iw * scale))), max(1, int(round(ih * scale)))
            thumb = im_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
            tx = x0 + 8 + (max_tw - nw) // 2
            ty = y0 + 32 + (max_th - nh) // 2
            canvas.paste(thumb, (tx, ty))

    # 6th slot: summary badge
    x0 = pad + 2 * (cw + pad)
    y0 = 52 + pad + 1 * (ch + pad)
    draw.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=10, fill="#EFF6FF", outline="#2563EB", width=2)
    draw.text((x0 + cw / 2, y0 + 60), "Built for Anti-Shortcut Eval", fill="#1D4ED8", font=get_font(17, bold=True), anchor="mm")
    bullets = [
        "• Seeded JSON Spec -> Exact Truth",
        "• Counterfactual Visual Twins (*_cf)",
        "• Redacted Hallucination Probes",
        "• Unlabeled Charts & Analog Dials",
        "• 5-Gate Grounding + 9/9 Mutants",
    ]
    for bi, b in enumerate(bullets):
        draw.text((x0 + 32, y0 + 108 + bi * 30), b, fill="#1E293B", font=get_font(14, bold=False))

    canvas.save(out_path)
    return True


def _draw_baseline_chart(summary: BenchmarkSummary, out_path: Path) -> None:
    models = summary.models_evaluated
    acc = [summary.overall_accuracy.get(m, 0.0) * 100 for m in models]
    cf = [summary.counterfactual_consistency.get(m, 0.0) * 100 for m in models]

    x = np.arange(len(models))
    width = 0.34
    fig_w = max(9.6, 1.9 * len(models))
    fig, ax = plt.subplots(figsize=(fig_w, 5.1), dpi=130)
    try:
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F8FAFC")
        b1 = ax.bar(x - width / 2, acc, width, label="Overall Accuracy (%)", color="#2563EB", zorder=3)
        b2 = ax.bar(x + width / 2, cf, width, label="Counterfactual Consistency (%)", color="#0D9488", zorder=3)
        ax.set_ylim(0, 120)
        ax.set_ylabel("Score (%)")
        ax.set_title("Blind Baselines & Real LLM Audit vs Multimodal Models", fontsize=13, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(models, fontsize=8.8, rotation=16 if len(models) > 3 else 0, ha="right" if len(models) > 3 else "center")
        ax.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for bars in (b1, b2):
            for bar in bars:
                v = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, v + 1.8, f"{v:.1f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")
        ax.legend(loc="upper left", frameon=True)
        fig.tight_layout()
        fig.savefig(out_path, dpi=130)
    finally:
        plt.close(fig)


def _draw_family_breakdown_chart(summary: BenchmarkSummary, out_path: Path) -> None:
    models = [m for m in summary.models_evaluated if m != "oracle_spec_verifier"]
    if not models:
        models = list(summary.models_evaluated)
    families = [f for f in ["charts", "spatial_inventory", "logic_circuits", "structured_docs", "blueprints_gauges"] if any(f in (summary.by_family.get(m, {})) for m in models)]
    label_map = {
        "charts": "Charts",
        "spatial_inventory": "Spatial",
        "logic_circuits": "Circuits",
        "structured_docs": "Invoices/Redacted",
        "blueprints_gauges": "Blueprints/Gauges",
    }
    fam_labels = [label_map.get(f, f) for f in families]
    palette = ["#64748B", "#94A3B8", "#A855F7", "#0EA5E9", "#2563EB", "#0D9488"]

    x = np.arange(len(families))
    n = len(models)
    width = min(0.18, 0.80 / max(1, n))

    fig, ax = plt.subplots(figsize=(11.2, 5.2), dpi=130)
    try:
        err_counts: dict[tuple[str, str], int] = {}
        tot_counts: dict[tuple[str, str], int] = {}
        for pred in summary.predictions:
            fam_prefix = pred.task_id.split("_")[0]
            # Map task_id prefix back to canonical family name
            for cand in families:
                if pred.task_id.startswith(cand):
                    tot_counts[(pred.model_name, cand)] = tot_counts.get((pred.model_name, cand), 0) + 1
                    if pred.error_category == "api_error":
                        err_counts[(pred.model_name, cand)] = err_counts.get((pred.model_name, cand), 0) + 1
                    break

        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F8FAFC")
        for idx, m in enumerate(models):
            vals = [summary.by_family.get(m, {}).get(f, 0.0) * 100 for f in families]
            offset = (idx - (n - 1) / 2.0) * width
            bars = ax.bar(x + offset, vals, width, label=m, color=palette[idx % len(palette)], zorder=3)
            for f_name, b in zip(families, bars):
                v = b.get_height()
                errs = err_counts.get((m, f_name), 0)
                tots = tot_counts.get((m, f_name), 0)
                lbl = "429*" if (tots > 0 and errs == tots) else (f"{v:.0f}%*" if errs > 0 else f"{v:.0f}%")
                ax.text(b.get_x() + b.get_width() / 2, v + 1.5, lbl, ha="center", va="bottom", fontsize=7, fontweight="bold")
        ax.set_ylim(0, 118)
        ax.set_ylabel("Accuracy (%)")
        ax.set_title("Where Multimodal Models Succeed vs Struggle (*429 = free-tier API quota cap)", fontsize=12.0, fontweight="bold", pad=46)
        ax.set_xticks(x)
        ax.set_xticklabels(fam_labels, fontsize=9.8)
        ax.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, 1.01),
            ncol=min(3, len(models)),
            fontsize=8.2,
            frameon=True,
        )
        fig.tight_layout()
        fig.savefig(out_path, dpi=130)
    finally:
        plt.close(fig)


def _draw_failure_spotlight(
    samples_dir: Path,
    summary: BenchmarkSummary,
    tasks: list[TaskPackage],
    out_path: Path,
) -> bool:
    task_map = {t.task_id: t for t in tasks}
    real_fails = [
        p
        for p in summary.predictions
        if p.provider not in {"diagnostic_baseline", "diagnostic_oracle", "blind_llm_audit"}
        and not p.correct
        and p.error_category != "api_error"
        and p.task_id in task_map
    ]
    if not real_fails:
        return False

    # Prefer distinct families and hard/complex spotlight failures
    picks = []
    seen_families: set[str] = set()
    prioritized = sorted(
        real_fails,
        key=lambda p: (
            0 if "hard" in p.task_id else (1 if "medium" in p.task_id else 2),
            0 if "flash-lite" not in p.model_name else 1,
        ),
    )
    for p in prioritized:
        fam = task_map[p.task_id].family.value
        if fam not in seen_families:
            picks.append(p)
            seen_families.add(fam)
        if len(picks) == 2:
            break
    for p in prioritized:
        if len(picks) >= 2:
            break
        if p not in picks:
            picks.append(p)

    w, h = 1320, 560
    canvas = Image.new("RGB", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    h_font = get_font(22, bold=True)
    hdr_font = get_font(12, bold=True)
    sub_font = get_font(13, bold=True)
    body_font = get_font(12, bold=False)

    draw.text((28, 16), "Diagnostic Failure Spotlight: Real Multimodal Model Mistakes Caught by Factory", fill="#0F172A", font=h_font)
    col_w = 620
    for idx, p in enumerate(picks):
        t = task_map[p.task_id]
        x0 = 28 + idx * (col_w + 24)
        y0 = 60
        draw.rounded_rectangle([x0, y0, x0 + col_w, h - 22], radius=10, fill="#FFF1F2", outline="#E11D48", width=2)
        hdr = f"{p.model_name}  |  {t.task_id}  ({t.reasoning_type})"
        draw.text((x0 + 14, y0 + 12), hdr, fill="#9F1239", font=hdr_font)
        draw.text((x0 + 14, y0 + 36), f"Expected: {p.expected_answer}   |   Model Predicted: {p.extracted_answer or 'EMPTY'}", fill="#0F172A", font=sub_font)
        q_short = (t.question[:88] + "...") if len(t.question) > 90 else t.question
        draw.text((x0 + 14, y0 + 60), f"Q: {q_short}", fill="#334155", font=body_font)
        img_p = samples_dir / t.image_path
        if img_p.exists():
            with Image.open(img_p) as im:
                im_rgb = im.convert("RGB")
                iw, ih = im_rgb.size
                max_tw, max_th = col_w - 28, 376
                scale = min(max_tw / iw, max_th / ih)
                nw, nh = max(1, int(round(iw * scale))), max(1, int(round(ih * scale)))
                thumb = im_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
                tx = x0 + 14 + (max_tw - nw) // 2
                ty = y0 + 88 + (max_th - nh) // 2
                canvas.paste(thumb, (tx, ty))

    canvas.save(out_path)
    return True
