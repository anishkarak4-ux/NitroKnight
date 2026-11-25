# Demo Video Script (3–4 Minutes)

Keep the video fast-paced, visual, and focused on **live proof** (repeatability + validation + VLM diagnostics).

## 0:00 – 0:30 | Hook & Problem
- Introduce your 3-member team and **Challenge 02: Visual Task Factory**.
- Explain the gap: *"Public VQA and chart benchmarks are heavily memorized. Innodata asked for a reusable factory that generates fresh visual tasks, verifies both question and answer inside the image, and reveals where multimodal AI actually struggles."*

## 0:30 – 1:30 | Live Repeatable Factory + Meaningful Variation (5 Families)
- Run in terminal:
  `vtf generate --out outputs/demo_suite --per-cell 1 --seed 46`
- Open the **Studio UI 2.0** (`vtf serve --dataset samples/demo_suite`).
- Click through all **5 visual families** (`charts`, `spatial_inventory`, `logic_circuits`, `structured_docs`, `blueprints_gauges`) and highlight hard failure triggers (e.g., unlabeled chart comparison, 5-input crossing schematics with semicircular bridge arcs, black-redacted `CANNOT_DETERMINE` abstention invoices, and architectural doorway shortest-path hops).
- Use the **Live Generate + Validate** panel with a brand-new seed (`999`) to prove nothing is hardcoded.

## 1:30 – 2:30 | Validation Evidence, Grounding Overlay & Twin Diff
- Filter by **VLM Failures Only** and select `logic_circuits_hard_s294_cf`.
- Toggle **Show Grounding Boxes** to show referenced elements and green answer evidence highlighted directly over pixels, plus **Side-by-Side Twin** comparing base `s294` (`A`) vs twin `s294_cf` (`E`).
- Show the **5 Automated Validation Gates** + `vtf audit-blind` (Ollama `mistral:latest` 7B blind audit scoring `0.0%`).

## 2:30 – 3:45 | Model Benchmarking & Failure Breakdown
- Inspect the **Per-Model Evaluation Responses** card in Studio UI 2.0 and `samples/demo_suite/benchmark_report.html`:
  - Show `blind_text_prior` (`10.0%`) and `blind_llm_mistral_latest` (`0.0%`) failing without images.
  - Show **Gemini 3.5 Flash-Lite** (`83.3%`, 0 errors) succeeding on Charts/Spatial/Redacted Docs while failing floorplan doorway hops (`blueprints_gauges_medium_s449`), and **Gemini 3.5 Flash** (`21/22 = 95.5%` valid calls) still failing the 5-pin crossing schematic (`s294_cf`, predicting `B` vs `E`).

## 3:45 – 4:00 | Wrap-up
- Briefly recap impact, public GitHub repo URL, `.github/workflows/ci.yml`, and `pytest` (`22 passed`) + `9/9` mutants killed.
