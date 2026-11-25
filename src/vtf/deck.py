"""Generates the branded 11-slide Innodata AI Hackathon submission PowerPoint deck."""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

TEMPLATE_PDF = Path("docs/Innodata _ IDEA SUBMISSION - Google Slides.pdf")
ASSETS_DIR = Path("docs/assets")
OUT_PPTX = Path("docs/NitroKnight_Visual_Task_Factory_Submission.pptx")

NAVY = RGBColor(15, 23, 42)
SLATE = RGBColor(51, 65, 85)
BLUE = RGBColor(37, 99, 235)
TEAL = RGBColor(13, 148, 136)
LIGHT_BG = RGBColor(248, 250, 252)
BORDER = RGBColor(203, 213, 225)
CARD_BLUE = RGBColor(239, 246, 255)
CARD_GREEN = RGBColor(236, 253, 245)


def _extract_clean_backgrounds() -> tuple[bytes, bytes, bytes]:
    """Render official slide backgrounds from template PDF with placeholder text masked out."""
    doc = pymupdf.open(TEMPLATE_PDF)

    def _render_page(idx: int, mask_box: tuple[float, float, float, float] | None = None) -> bytes:
        page = doc[idx]
        zoom = 2.5
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        if mask_box is not None:
            draw = ImageDraw.Draw(im)
            x0, y0, x1, y1 = [int(v * zoom) for v in mask_box]
            draw.rectangle([x0, y0, x1, y1], fill="#FFFFFF")
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()

    cover_bg = _render_page(0, mask_box=(20, 245, 700, 382))
    content_bg = _render_page(6, mask_box=(15, 55, 705, 385))
    thankyou_bg = _render_page(10, mask_box=None)
    return cover_bg, content_bg, thankyou_bg


def _add_bg(slide, img_bytes: bytes, w: Inches, h: Inches) -> None:
    slide.shapes.add_picture(io.BytesIO(img_bytes), Inches(0), Inches(0), width=w, height=h)


def _add_title(slide, text: str) -> None:
    tb = slide.shapes.add_textbox(Inches(0.45), Inches(0.68), Inches(9.1), Inches(0.45))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = text
    r.font.name = "DejaVu Sans"
    r.font.size = Pt(20)
    r.font.bold = True
    r.font.color.rgb = NAVY


def _add_bullets(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    items: list[tuple[str, str]],
    font_pt: int = 12,
) -> None:
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for idx, (lead, body) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(7)
        r1 = p.add_run()
        r1.text = f"• {lead}: " if lead else "• "
        r1.font.name = "DejaVu Sans"
        r1.font.size = Pt(font_pt)
        r1.font.bold = True
        r1.font.color.rgb = NAVY

        r2 = p.add_run()
        r2.text = body
        r2.font.name = "DejaVu Sans"
        r2.font.size = Pt(font_pt)
        r2.font.color.rgb = SLATE


def _add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    body: str,
    fill_rgb: RGBColor = LIGHT_BG,
    accent_rgb: RGBColor = BLUE,
) -> None:
    rect = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    rect.fill.solid()
    rect.fill.fore_color.rgb = fill_rgb
    rect.line.color.rgb = BORDER
    rect.line.width = Pt(1.0)
    tf = rect.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.14)
    tf.margin_right = Inches(0.14)
    tf.margin_top = Inches(0.12)

    p0 = tf.paragraphs[0]
    p0.space_after = Pt(5)
    r0 = p0.add_run()
    r0.text = title
    r0.font.name = "DejaVu Sans"
    r0.font.size = Pt(12.5)
    r0.font.bold = True
    r0.font.color.rgb = accent_rgb

    p1 = tf.add_paragraph()
    r1 = p1.add_run()
    r1.text = body
    r1.font.name = "DejaVu Sans"
    r1.font.size = Pt(10.5)
    r1.font.color.rgb = SLATE


def _fit_picture(slide, img_path: Path, left: float, top: float, max_w: float, max_h: float) -> None:
    with Image.open(img_path) as im:
        iw, ih = im.size
    ratio = min(max_w / iw, max_h / ih)
    pw, ph = iw * ratio, ih * ratio
    x = left + (max_w - pw) / 2
    y = top + (max_h - ph) / 2
    slide.shapes.add_picture(str(img_path), Inches(x), Inches(y), width=Inches(pw), height=Inches(ph))


def build_submission_deck(out_path: Path = OUT_PPTX) -> Path:
    cover_bg, content_bg, thankyou_bg = _extract_clean_backgrounds()
    prs = Presentation()
    prs.slide_width = Inches(10.0)
    prs.slide_height = Inches(5.625)
    blank = prs.slide_layouts[6]
    w, h = prs.slide_width, prs.slide_height

    # Slide 1 — Cover
    s1 = prs.slides.add_slide(blank)
    _add_bg(s1, cover_bg, w, h)
    tb = s1.shapes.add_textbox(Inches(0.5), Inches(3.52), Inches(9.0), Inches(1.75))
    tf = tb.text_frame
    tf.word_wrap = True
    for idx, (k, v) in enumerate([
        ("Team Name : ", "NitroKnight"),
        ("Team Leader Name : ", "Anish Karak  (Team Size: 3 Members)"),
        ("Problem Statement : ", "Challenge 02 — Visual Task Factory"),
    ]):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        rk = p.add_run()
        rk.text = k
        rk.font.name = "DejaVu Sans"
        rk.font.size = Pt(16)
        rk.font.bold = True
        rk.font.color.rgb = NAVY
        rv = p.add_run()
        rv.text = v
        rv.font.name = "DejaVu Sans"
        rv.font.size = Pt(16)
        rv.font.color.rgb = BLUE if idx == 2 else SLATE

    # Slide 2 — Brief about the Idea
    s2 = prs.slides.add_slide(blank)
    _add_bg(s2, content_bg, w, h)
    _add_title(s2, "Brief about the Idea")
    _add_bullets(
        s2, 0.45, 1.25, 9.1, 1.45,
        [
            ("What We Built", "Visual Task Factory (VTF) — a reusable, deterministic pipeline that synthesizes diverse visual reasoning tasks, verifies answers against pixel-level scene manifests, and diagnoses where multimodal AI succeeds or struggles."),
            ("Spec-First Ground Truth", "Generates PNG images, JSON specs, symbolic solver traces, and counterfactual visual twins from seeds — never hardcoded static examples."),
        ],
        font_pt=12,
    )
    _add_card(s2, 0.45, 2.85, 2.9, 2.2, "5 Families + Perturbations", "Charts, Spatial/Occlusion, 5-Pin Circuits/DAGs, Redacted Docs & Floorplans/Gauges (+ Scan-Tilt & Noise tests).", CARD_BLUE, BLUE)
    _add_card(s2, 3.55, 2.85, 2.9, 2.2, "5-Gate + Blind LLM + Scale", "Verifies bounds, overlap, grounding, solver parity, Ollama Mistral blind audit (0%) & 150/150 scale zero collisions.", CARD_GREEN, TEAL)
    _add_card(s2, 6.65, 2.85, 2.9, 2.2, "4-Tier VLM + Abstention Eval", "Benchmarks Mistral (0%) -> Qwen2.5-VL 3B (56.7%) -> Flash-Lite (83.3%) -> Flash (95.5% att.) + Wilson 95% CI.", CARD_BLUE, BLUE)

    # Slide 3 — Opportunity & USP
    s3 = prs.slides.add_slide(blank)
    _add_bg(s3, content_bg, w, h)
    _add_title(s3, "Opportunity, Differentiation & USP")
    _add_bullets(
        s3, 0.45, 1.22, 9.1, 2.45,
        [
            ("Problem With Existing Benchmarks", "Static datasets (VQA v2, ChartQA, CLEVR) suffer from memorization, text-only priors, clean-only bias, and guessing on redacted docs."),
            ("Zero Diffusion Hallucination", "Programmatic Matplotlib/Pillow synthesis + bbox-aware scan/noise perturbations keep ground truth exact under degradation."),
            ("Counterfactual Twins + Redacted Abstention", "Every task emits an answer-flipping twin (*_cf) plus black-redacted audits expecting CANNOT_DETERMINE (0% VLM hallucination)."),
            ("Empirical 4-Tier Capability Ladder", "Blind regex (10.0%) & Ollama Mistral (0.0%) < Qwen2.5-VL 3B (56.7%) < Flash-Lite (83.3%) < Flash (95.5% attempted, 21/22) < Oracle (100%)."),
        ],
        font_pt=10.6,
    )
    _add_card(s3, 0.45, 3.85, 4.4, 1.25, "150/150 Factory Scale Proof", "Generates 150 valid tasks (75 pairs) in 9.16s (16.37 tasks/sec) with 100% pass rate & 0 SHA-256 collisions.", CARD_GREEN, TEAL)
    _add_card(s3, 5.15, 3.85, 4.4, 1.25, "Green CI, Docker & Mutation Proof", "GitHub Actions CI (verify + Docker container build/run passing), 25+ pytest checks & 9/9 mutants killed.", CARD_BLUE, BLUE)

    # Slide 4 — List of Features + 5-Family Showcase
    s4 = prs.slides.add_slide(blank)
    _add_bg(s4, content_bg, w, h)
    _add_title(s4, "Key Features & Meaningful Variation (5 Visual Families)")
    _add_bullets(
        s4, 0.45, 1.25, 3.9, 3.85,
        [
            ("1. Charts", "OCR-proof unlabeled visual gap charts, grouped, stacked, line & dual-axis combo."),
            ("2. Spatial & Occlusion", "Warehouse inventory racks & CLEVR 2D scenes with z-order depth tests."),
            ("3. Logic & Flow", "5-input dense wire-crossing schematics w/ bridge arcs, faults & flow DAGs."),
            ("4. Invoices & Redacted", "Cross-column discrepancy auditing + redacted CANNOT_DETERMINE abstention."),
            ("5. Blueprints & Gauges", "Floorplan room dimensions, doorway shortest-path hops & analog dial needles."),
        ],
        font_pt=10,
    )
    _fit_picture(s4, ASSETS_DIR / "families_showcase.png", 4.45, 1.18, 5.2, 4.0)

    # Slide 5 — Process Flow & Empirical Failure Insights
    s5 = prs.slides.add_slide(blank)
    _add_bg(s5, content_bg, w, h)
    _add_title(s5, "Process Flow & Empirical Model Failure Insights")
    _add_bullets(
        s5, 0.45, 1.15, 9.1, 1.45,
        [
            ("End-to-End Flow", "Seeded Spec -> Render/Perturb + Manifest -> Solver -> 5-Gate Validator -> Twins -> VLM Eval -> MD/JSON/HTML + Wilson CI."),
            ("Blind Audits & Open-Weights VLM", "Mistral-7B blind LLM scores 0.0%; local Qwen2.5-VL 3B hits 56.7% (100% Charts & Abstention, but 33% Circuits & Blueprints)."),
            ("Gemini 3.5 Flash-Lite (30/30, 0 Errors)", "83.3% overall (73.3% CF, 0% hallucination): 100% Charts/Spatial/Docs, 66.7% Blueprints (door hops) & 50.0% Circuits."),
            ("Gemini 3.5 Flash (21/22 Att. = 95.5%)", "70.0% strict (8 free-tier 429 caps): aced medium DAGs, yet ALL 3 real VLMs failed 5-pin crossing schematic s294_cf (D/C/B vs E)!"),
        ],
        font_pt=9.4,
    )
    _fit_picture(s5, ASSETS_DIR / "model_failure_breakdown.png", 0.40, 2.66, 4.55, 2.52)
    _fit_picture(s5, ASSETS_DIR / "failure_spotlight.png", 5.05, 2.66, 4.55, 2.52)

    # Slide 6 — Studio UI Screenshot
    s6 = prs.slides.add_slide(blank)
    _add_bg(s6, content_bg, w, h)
    _add_title(s6, "Studio UI 2.0: Live Probe, SVG Grounding, Twin Diff & Failure Filter")
    _fit_picture(s6, ASSETS_DIR / "studio_ui_screenshot.png", 0.45, 1.15, 9.1, 4.08)

    # Slide 7 — Architecture Diagram
    s7 = prs.slides.add_slide(blank)
    _add_bg(s7, content_bg, w, h)
    _add_title(s7, "Architecture Diagram of the Proposed Solution")
    _fit_picture(s7, ASSETS_DIR / "architecture_diagram.png", 0.35, 1.18, 9.3, 4.05)

    # Slide 8 — Technologies Used
    s8 = prs.slides.add_slide(blank)
    _add_bg(s8, content_bg, w, h)
    _add_title(s8, "Technologies Used in the Solution")
    _add_card(s8, 0.45, 1.28, 4.4, 1.8, "Synthesis, Perturbations & BBoxes", "Python 3.12, Pydantic v2, Matplotlib/Pillow, NumPy, deterministic `scan_tilt` & `low_contrast_jpeg` perturbations preserving manifests.", CARD_BLUE, BLUE)
    _add_card(s8, 5.15, 1.28, 4.4, 1.8, "Validation, Audits & 150-Task Scale", "5-Gate Validator, Ollama `mistral:latest` blind audit, 25 pytest tests, 9/9 mutants killed & 150-task zero-collision stress suite.", CARD_GREEN, TEAL)
    _add_card(s8, 0.45, 3.28, 4.4, 1.8, "4-Tier VLM Harness & Statistics", "JSONL cache, Gemini Flash/Lite + Ollama Vision (`qwen2.5vl:3b`), Attempted Acc, 95% Wilson CI, Failure Taxonomy & HTML reports.", CARD_GREEN, TEAL)
    _add_card(s8, 5.15, 3.28, 4.4, 1.8, "Studio UI 2.0, CLI & Docker CI", "FastAPI Studio (`/report`, Live Single-Task Probe, `VLM Failures Only`, Twin Diff), `vtf` CLI & GitHub Actions Docker CI.", CARD_BLUE, BLUE)

    # Slide 9 — Implementation Cost, Baseline Ladder & Robustness/Scale Chart
    s9 = prs.slides.add_slide(blank)
    _add_bg(s9, content_bg, w, h)
    _add_title(s9, "Implementation Cost, Capability Ladder & Robustness Telemetry")
    _add_bullets(
        s9, 0.45, 1.15, 9.1, 1.40,
        [
            ("Zero-Cost Generation & Audits ($0)", "150 tasks generated in 9.16s (16.4 tasks/s, 0 collisions) + local Ollama Mistral-7B & Qwen2.5-VL 3B ($0 API cost)."),
            ("Free-Tier Prototyping + Scaling", "Completed Gemini 3.5 Flash-Lite (83.3%) & Qwen2.5-VL 3B (56.7%); resumable cache scales cleanly with finalist credits."),
            ("Perturbation Robustness Sweep", "Flash-Lite holds 70.0% on Scan Tilt (+/-2 deg, Q76) and drops to 60.0% on Low-Contrast Noisy JPEG (Q38) on DAG edges."),
        ],
        font_pt=9.6,
    )
    _fit_picture(s9, ASSETS_DIR / "validation_and_baselines.png", 0.35, 2.62, 4.65, 2.55)
    _fit_picture(s9, ASSETS_DIR / "robustness_and_scale.png", 5.05, 2.62, 4.60, 2.55)

    # Slide 10 — Hackathon Deliverables Checklist
    s10 = prs.slides.add_slide(blank)
    _add_bg(s10, content_bg, w, h)
    _add_title(s10, "Deliverables & Validation Evidence Summary")
    _add_bullets(
        s10, 0.45, 1.25, 9.1, 3.9,
        [
            ("Runnable Code, Docker & Passing CI", "Public repo (`github.com/anishkarak4-ux/NitroKnight`) with `Dockerfile` + GitHub Actions CI (`verify` + `docker` build/run jobs)."),
            ("Sample Outputs (`samples/demo_suite`)", "30 validated tasks across 5 families x 3 tiers + `benchmark_report.{md,json,html}`, `scale_report.json` (150 tasks) & `robustness_report.json`."),
            ("Validation & Mutation Evidence", "Full pytest suite passes; 30/30 + 150/150 scale tasks pass 5-gate validation; 9/9 mutants killed (`mutation_report.json`)."),
            ("7-Model Empirical Insights", "Mistral Blind (0.0%) < Qwen2.5-VL 3B (56.7%) < Flash-Lite (83.3%) < Flash (95.5% attempted) < Oracle (100%) + Wilson 95% CI."),
            ("Technical Explanation & Live Studio", "`docs/ARCHITECTURE.md`, `docs/VALIDATION_EVIDENCE.md`, `docs/DEMO_SCRIPT.md`, & FastAPI Studio Live Probe."),
        ],
        font_pt=10.2,
    )

    # Slide 11 — Thank You
    s11 = prs.slides.add_slide(blank)
    _add_bg(s11, thankyou_bg, w, h)
    tb11 = s11.shapes.add_textbox(Inches(0.8), Inches(4.78), Inches(8.6), Inches(0.45))
    tf11 = tb11.text_frame
    p11 = tf11.paragraphs[0]
    p11.alignment = PP_ALIGN.LEFT
    r11 = p11.add_run()
    r11.text = "Team NitroKnight  |  Challenge 02: Visual Task Factory  |  github.com/anishkarak4-ux/NitroKnight"
    r11.font.name = "DejaVu Sans"
    r11.font.size = Pt(11.5)
    r11.font.bold = True
    r11.font.color.rgb = RGBColor(226, 232, 240)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return out_path


if __name__ == "__main__":
    p = build_submission_deck()
    print(f"Generated {p}")
