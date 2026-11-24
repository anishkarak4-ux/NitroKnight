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
    _add_card(s2, 0.45, 2.85, 2.9, 2.2, "4 Visual Families", "Charts, Spatial & Occlusion, Logic Circuits & Flow DAGs, Invoices & QA Matrices across Easy / Medium / Hard.", CARD_BLUE, BLUE)
    _add_card(s2, 3.55, 2.85, 2.9, 2.2, "5-Gate Validator + Mutants", "Verifies bounds, readability/zero overlap, strict Q/A visual grounding, solver parity, and anti-shortcut leakage (9/9 mutants killed).", CARD_GREEN, TEAL)
    _add_card(s2, 6.65, 2.85, 2.9, 2.2, "Real VLM Diagnostics", "Evaluates Gemini Flash, OpenAI/OpenRouter & Ollama Vision vs blind text baselines with Counterfactual Consistency.", CARD_BLUE, BLUE)

    # Slide 3 — Opportunity & USP
    s3 = prs.slides.add_slide(blank)
    _add_bg(s3, content_bg, w, h)
    _add_title(s3, "Opportunity, Differentiation & USP")
    _add_bullets(
        s3, 0.45, 1.22, 9.1, 2.0,
        [
            ("Problem With Existing Benchmarks", "Static datasets (VQA v2, ChartQA, CLEVR) suffer from web pretraining leakage and text-only language priors where models guess without looking at pixels."),
            ("Zero Diffusion Hallucination", "Programmatic Matplotlib/Pillow synthesis guarantees exact numbers, labels, wire connections, and z-order occlusion — impossible with diffusion image generators."),
            ("Counterfactual Visual Twin Engine", "Every task emits a minimally altered twin (*_cf) that flips the answer, measuring whether VLMs actually inspect pixels rather than memorizing priors."),
            ("Empirical Anti-Shortcut Proof", "Blind text-only baseline scores just 8.3% overall (0.0% counterfactual consistency), vs 83.3%–91.7% for Gemini Flash models and 100.0% for our symbolic verifier."),
        ],
        font_pt=11,
    )
    _add_card(s3, 0.45, 3.85, 4.4, 1.25, "Strict Grounding Guarantee", "Every queried element and evidence region has an exact bounding box in SceneManifest (`100%` grounding coverage).", CARD_GREEN, TEAL)
    _add_card(s3, 5.15, 3.85, 4.4, 1.25, "Judge-Ready Reproducibility", "Seeded deterministic generation + 19/19 pytest checks + 9/9 mutation fault detection + standardized Dockerfile.", CARD_BLUE, BLUE)

    # Slide 4 — List of Features + 4-Family Showcase
    s4 = prs.slides.add_slide(blank)
    _add_bg(s4, content_bg, w, h)
    _add_title(s4, "Key Features & Meaningful Variation (4 Visual Families)")
    _add_bullets(
        s4, 0.45, 1.25, 3.9, 3.85,
        [
            ("1. Charts", "Grouped, stacked, line & dual-axis combo charts with unlabeled axis-reading."),
            ("2. Spatial & Occlusion", "Warehouse inventory racks & CLEVR 2D scenes with z-order depth tests."),
            ("3. Logic & Flow", "Multi-stage boolean schematics, fault sensitivity & open/blocked DAGs."),
            ("4. Invoices & QA", "Checkbox filtering & cross-column arithmetic discrepancy auditing."),
            ("5. Integrated Runner", "CLI + FastAPI Studio + counterfactual pairs + Markdown/JSON reports."),
        ],
        font_pt=10,
    )
    _fit_picture(s4, ASSETS_DIR / "families_showcase.png", 4.45, 1.18, 5.2, 4.0)

    # Slide 5 — Process Flow & Failure Breakdown
    s5 = prs.slides.add_slide(blank)
    _add_bg(s5, content_bg, w, h)
    _add_title(s5, "Process Flow & Empirical Model Failure Insights")
    _add_bullets(
        s5, 0.45, 1.22, 3.8, 3.9,
        [
            ("Pipeline Steps", "Seeded Spec -> Render + Manifest -> Symbolic Solver -> 5-Gate Validator -> Counterfactual Pair -> VLM Benchmark."),
            ("Blind Baseline", "8.3% overall (0.0% CF consistency) confirms zero language-prior shortcuts."),
            ("Gemini 3.5 Flash-Lite", "83.3% overall: 100% on Charts, Spatial & Invoices, but drops to 33.3% on Logic Circuits & Flow DAGs."),
            ("Gemini 3 Flash Preview", "91.7% overall (100% on 22/22 answered calls; final 2 hit free-tier 429 quota)."),
        ],
        font_pt=10,
    )
    _fit_picture(s5, ASSETS_DIR / "model_failure_breakdown.png", 4.35, 1.2, 5.3, 3.95)

    # Slide 6 — Studio UI Screenshot
    s6 = prs.slides.add_slide(blank)
    _add_bg(s6, content_bg, w, h)
    _add_title(s6, "Interactive Studio UI & Pixel Grounding Overlay (`vtf serve`)")
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
    _add_card(s8, 0.45, 1.28, 4.4, 1.8, "Synthesis & Exact Rendering", "Python 3.12, Pydantic v2, Matplotlib (Agg renderer window extents for bbox extraction), Pillow (anti-aliased schematics, racks, invoices, DejaVuSans typography), NumPy.", CARD_BLUE, BLUE)
    _add_card(s8, 5.15, 1.28, 4.4, 1.8, "Validation & Mutation Testing", "5-Gate Validator (bounds, overlap, grounding, independent solver, leakage), pytest (19 tests), and 9-Mutant Fault Injection Suite (`vtf mutate`, 100% kill rate).", CARD_GREEN, TEAL)
    _add_card(s8, 0.45, 3.28, 4.4, 1.8, "Multimodal Evaluation Harness", "Pluggable adapters for Google Gemini REST/SDK, OpenAI/OpenRouter/Groq, Local Ollama Vision (`qwen2.5vl:3b` / `moondream`), plus offline diagnostic baselines.", CARD_GREEN, TEAL)
    _add_card(s8, 5.15, 3.28, 4.4, 1.8, "Studio UI, CLI & Packaging", "FastAPI, Uvicorn, HTTPX, interactive HTML5/SVG grounding overlay, unified `vtf` CLI, and standardized Docker container (`Dockerfile`).", CARD_BLUE, BLUE)

    # Slide 9 — Implementation Cost & Baseline Chart
    s9 = prs.slides.add_slide(blank)
    _add_bg(s9, content_bg, w, h)
    _add_title(s9, "Estimated Implementation Cost & Solvability Verification")
    _add_bullets(
        s9, 0.45, 1.25, 3.8, 3.85,
        [
            ("Generation & Validation ($0)", "100% deterministic CPU execution; zero paid image-generation APIs required."),
            ("Prototyping Cost ($0)", "Evaluated via free Google AI Studio tier (Gemini 3.5 Flash-Lite & Gemini 3 Flash Preview) and optional local Ollama vision."),
            ("Scalable Evaluation", "Ready to benchmark frontier models at larger scale using finalist credits."),
        ],
        font_pt=10.5,
    )
    _fit_picture(s9, ASSETS_DIR / "validation_and_baselines.png", 4.35, 1.22, 5.3, 3.9)

    # Slide 10 — Hackathon Deliverables Checklist
    s10 = prs.slides.add_slide(blank)
    _add_bg(s10, content_bg, w, h)
    _add_title(s10, "Deliverables & Validation Evidence Summary")
    _add_bullets(
        s10, 0.45, 1.25, 9.1, 3.9,
        [
            ("Runnable Source Code + Docker", "Public GitHub repo (`github.com/anishkarak4-ux/NitroKnight`) with `pyproject.toml`, `Dockerfile`, CLI (`vtf`), and FastAPI Studio (`vtf serve`)."),
            ("Sample Outputs (`samples/demo_suite`)", "24 validated tasks (12 base + 12 counterfactual twins) across 4 families × 3 difficulties with pixel manifests and solver traces."),
            ("Validation & Mutation Evidence", "19/19 pytest tests pass; 24/24 tasks pass 5-gate validation; 9/9 fault-injection mutants killed (`mutation_report.json`)."),
            ("Live Model Evaluation Findings", "Full benchmark table & failure taxonomy (`benchmark_report.md`) contrasting blind priors (8.3%) vs Gemini VLMs (83.3%–91.7%) vs Oracle (100%)."),
            ("Technical Explanation & Demo", "Architecture spec (`docs/ARCHITECTURE.md`), validation summary (`docs/VALIDATION_EVIDENCE.md`), and live walkthrough (`docs/DEMO_SCRIPT.md`)."),
        ],
        font_pt=11,
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
