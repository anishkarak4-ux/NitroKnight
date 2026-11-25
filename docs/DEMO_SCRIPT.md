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

## 1:30 – 2:30 | Validation Evidence, Grounding Overlay, Live Probe & Twin Diff
- Filter by **VLM Failures Only** and select `logic_circuits_hard_s294_cf`.
- Toggle **Show Grounding Boxes** to show referenced elements and green answer evidence highlighted directly over pixels, plus **Side-by-Side Twin** comparing base `s294` (`A`) vs twin `s294_cf` (`E`).
- Click **Evaluate Selected Task Live** (`oracle` or `ollama:qwen2.5vl:3b`) to prove instant live evaluation against the symbolic solver.
- Show `vtf stress-test --per-cell 5` (**150/150 valid, 0 collisions in ~9s**) + `vtf audit-blind` (`mistral:latest` `0.0%`).

## 2:30 – 3:45 | 7-Model Benchmark & Failure Breakdown
- Click **Full HTML Report ↗** (`/report`) and inspect the **Per-Model Evaluation Responses** card in Studio UI 2.0:
  - Contrast the 4-tier capability ladder: `blind_llm_mistral_latest` (**0.0%**) < local `qwen2.5vl:3b` (**56.7%**) < `gemini-3.5-flash-lite` (**83.3%**) < `gemini-3.5-flash` (**95.5% attempted**, `21/22`).
  - Point out how **all 3 VLMs failed `logic_circuits_hard_s294_cf`** (`D` / `C` / `B` vs `E`), plus our `scan_tilt` vs `low_contrast_jpeg` perturbation sweep (`70% -> 60%`).

## 3:45 – 4:00 | Wrap-up
- Briefly recap impact, public GitHub repo URL, green `.github/workflows/ci.yml` (`verify` + `docker`), and `pytest` (`25 passed`) + `9/9` mutants killed.
