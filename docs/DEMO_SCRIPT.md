# Demo Video Script (3–4 Minutes)

Keep the video fast-paced, visual, and focused on **live proof** (repeatability + validation + VLM diagnostics).

## 0:00 – 0:30 | Hook & Problem
- Introduce your 3-member team and **Challenge 02: Visual Task Factory**.
- Explain the gap: *"Public VQA and chart benchmarks are heavily memorized. Innodata asked for a reusable factory that generates fresh visual tasks, verifies both question and answer inside the image, and reveals where multimodal AI actually struggles."*

## 0:30 – 1:30 | Live Repeatable Factory + Meaningful Variation
- Run in terminal:
  `vtf generate --out outputs/demo_suite --per-cell 2 --seed 42`
- Open the **Studio UI** (`vtf serve --dataset outputs/demo_suite`).
- Click through all **4 visual families** (`charts`, `spatial_inventory`, `logic_circuits`, `structured_docs`) and highlight different reasoning types (e.g., dual-axis conditional filtering, z-order occlusion, boolean fault sensitivity, invoice discrepancy auditing).
- Use the **Live Generate + Validate** panel with a brand-new seed (`999`) to prove nothing is hardcoded.

## 1:30 – 2:30 | Validation Evidence & Grounding Overlay
- Toggle **Show Grounding Boxes** in the Studio UI to show every referenced object and answer evidence highlighted directly on the pixels.
- Show the **5 Automated Validation Gates** passing + the **Independent Symbolic Solver Trace**.
- Show a **Counterfactual Twin (`*_cf`)** side-by-side with its base task, pointing out how one small visual edit flips the verified answer.

## 2:30 – 3:45 | Model Benchmarking & Failure Breakdown
- Run evaluation in terminal or Studio UI:
  - Show `blind_text_prior` failing (proving the tasks cannot be cheated without looking at the image).
  - Show real VLM results (e.g. `gemini:gemini-3.6-flash` or `ollama:qwen2.5vl:3b`) and inspect `benchmark_report.md` / Studio summary table — highlight which families/difficulties the VLM aced vs where it failed (such as circuit wire tracing or counterfactual pairs).

## 3:45 – 4:00 | Wrap-up
- Briefly recap impact, public GitHub repo URL, and test suite passing (`pytest`).
