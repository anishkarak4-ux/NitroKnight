# Visual Task Factory (Innodata AI Hackathon — Challenge 02)

[![Visual Task Factory CI](https://github.com/anishkarak4-ux/NitroKnight/actions/workflows/ci.yml/badge.svg)](https://github.com/anishkarak4-ux/NitroKnight/actions/workflows/ci.yml)

A **reusable, Dockerized, deterministic visual evaluation factory** that synthetically generates diverse multimodal visual reasoning tasks, enforces a **5-gate automated validation pipeline** + **real blind-LLM audit** (verified via **9/9 mutation testing** and **150-task zero-collision scale stress tests**), generates **counterfactual visual twin pairs**, **redacted abstention checks**, and **scan/noise robustness perturbations**, and benchmarks multimodal AI models with **Attempted Accuracy, 95% Wilson CI, and Failure Taxonomy**.

---

## Submission Deliverables Map (Official Spec Aligned)

| Official Requirement | Included Location |
|---|---|
| **Runnable Source Code, Docker & CI** | [src/vtf/](src/vtf/), [Dockerfile](Dockerfile), [.github/workflows/ci.yml](.github/workflows/ci.yml) (`verify` + `docker` CI jobs), [pyproject.toml](pyproject.toml) |
| **Sample Outputs & Findings** | [samples/demo_suite/](samples/demo_suite/) (30 tasks, PNGs, `benchmark_report.{md,json,html}`, `scale_report.json`, `robustness_report.json`, `predictions_cache.jsonl`) |
| **Validation & Mutation Evidence** | [tests/](tests/), [docs/VALIDATION_EVIDENCE.md](docs/VALIDATION_EVIDENCE.md), [samples/demo_suite/mutation_report.json](samples/demo_suite/mutation_report.json), `vtf validate`, `vtf audit-blind`, `vtf mutate`, `vtf stress-test` |
| **Technical Explanation & Deck** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PITCH_OUTLINE.md](docs/PITCH_OUTLINE.md), [docs/NitroKnight_Visual_Task_Factory_Submission.pptx](docs/NitroKnight_Visual_Task_Factory_Submission.pptx) |
| **Demo Walkthrough Script** | [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) |

---

## Key Features & Engineering Highlights

### 1. Meaningful Variation Across 5 Visual Families × 3 Difficulty Tiers
| Family | Subtypes | Visual & Reasoning Challenges |
|---|---|---|
| **`charts`** | Vertical, Horizontal, Grouped, Line, Stacked, Dual-axis combo, Unlabeled gap charts | Extrema, threshold counting, series differences, net growth, dual-axis filtering, OCR-proof unlabeled visual bar gap comparison |
| **`spatial_inventory`** | Warehouse storage racks, CLEVR-inspired compositional geometric scenes | Attribute-filtered counting, inventory summing, left/right spatial anchors, pattern recognition, z-order occlusion depth |
| **`logic_circuits`** | 5-input dense wire-crossing boolean schematics w/ semicircular bridge arcs, Directed open/blocked DAGs | Signal tracing across non-connecting crossovers, 5-pin fault sensitivity, Dijkstra shortest path over open edges |
| **`structured_docs`** | Purchase invoices, Redacted audit ledgers, Hardware QA inspection matrices | Cell lookup, drawn checkbox filtering, cross-column arithmetic discrepancy auditing, **`CANNOT_DETERMINE` hallucination abstention** on black-masked cells |
| **`blueprints_gauges`** | Architectural floorplan blueprints, Multi-dial analog pressure/voltage gauge clusters | Metric room area summation, wall-vs-doorway BFS hop shortest path, analog needle threshold zone counting & continuous value estimation |

### 2. Five-Gate Automated Validator + Real Blind LLM Audit (`src/vtf/validator.py`)
Every generated task passes five independent checks before entering the suite:
1. **`image_integrity_and_bounds`**: Verifies image dimensions and ensures all rendered elements lie strictly within `[0, W] × [0, H]`.
2. **`visual_readability_and_overlap`**: Enforces minimum queried font sizes and detects overlapping text/tick labels using actual rendered pixel bounding boxes (`matplotlib` renderer extents & `Pillow` geometry).
3. **`strict_qa_grounding`**: Ensures every referenced entity and answer evidence ID is present in `SceneManifest` and visibly rendered.
4. **`independent_solver_verification`**: Re-computes the exact ground-truth answer independently from the canonical JSON spec and records a step-by-step `solver_trace`.
5. **`anti_shortcut_leakage_audit`**: Rejects verbatim answer leakage, evaluates deterministic regex priors, and supports real image-less LLM auditing (`vtf audit-blind` via local Ollama `mistral:latest` -> `0.0%` accuracy).

### 3. Mutation Testing (`vtf mutate`) & 150-Task Scale Stress Test (`vtf stress-test`)
Proves the validator and answer scorer catch deliberately injected faults with a **100% kill rate (9/9 mutants killed)**, and `vtf stress-test --per-cell 5` verifies **150 / 150 valid tasks (75 counterfactual pairs, 100% pass rate, 0 image hash collisions)** generated in **9.16s (`16.37 tasks/sec`)**.

### 4. Counterfactual Twins, Scan Perturbations (`vtf perturb`) & Studio UI 2.0
- Every base task generates a **minimal visual twin** that flips the verified answer (`samples/demo_suite` = 15 base + 15 twins across all 15 unique reasoning types).
- **Real-World Perturbation Robustness:** `vtf perturb --mode scan_tilt|low_contrast_jpeg` applies deterministic camera tilt (`±2°` + JPEG quantization) and low-contrast sensor noise while transforming `SceneManifest` bboxes.
- **Resumable Cache, Statistical CI & HTML Reporting:** `vtf evaluate` caches valid results in `predictions_cache.jsonl`, separates **Strict vs. Attempted Accuracy** (excluding API errors), computes **95% Wilson CI**, classifies failures via **Error Taxonomy**, and writes MD/JSON/HTML reports.
- **Pluggable Models:** **Google Gemini** (`gemini:gemini-3.5-flash-lite`, `gemini:gemini-3.5-flash`), **OpenAI / OpenRouter / Groq**, **Local Ollama Vision & Blind Audits** (`ollama:qwen2.5vl:3b`, `ollama_blind:mistral:latest`), plus `blind_prior`, `pixel_heuristic`, and `oracle`.
- **Studio UI 2.0 (`vtf serve`):** Includes Family/Difficulty/**VLM Failures Only** filters, **Side-by-Side Counterfactual Twin** viewer, SVG grounding overlay, **Live Single-Task VLM Probe** (`/api/evaluate-one`), and one-click **`/report`** HTML viewer.

---

## Quickstart

### Option A: Local Python Setup
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

pip install -r requirements.txt
pip install -e . --no-deps
```

### Option B: Standardized Docker Execution (Recommended for Judges)
```bash
docker build -t visual-task-factory .
docker run --rm visual-task-factory
```
To launch the interactive Studio UI inside Docker:
```bash
docker run --rm -p 8000:8000 visual-task-factory vtf serve --dataset samples/demo_suite --host 0.0.0.0 --port 8000
```

---

## CLI Workflow

```bash
# 1. Generate a repeatable validated suite (30 tasks = 15 unique types + 15 counterfactual twins)
vtf generate --out outputs/demo_suite --per-cell 1 --seed 46

# 2. Verify all 5 validation gates pass on the suite
vtf validate --dataset outputs/demo_suite

# 3. Prove tasks cannot be solved without images using a real local LLM (requires Ollama)
vtf audit-blind --dataset outputs/demo_suite --model mistral:latest

# 4. Run mutation testing + 150-task scale throughput stress test
vtf mutate --out outputs/demo_suite/mutation_report.json
vtf stress-test --per-cell 5 --seed 100 --out outputs/demo_suite/scale_report.json

# 5. Generate scan/noise-perturbed robustness suite & benchmark
vtf perturb --dataset samples/demo_suite --mode scan_tilt --out outputs/demo_scan_tilt

# 6. Benchmark local Ollama Vision, offline baselines & Gemini VLMs (resumable cache + HTML report)
vtf evaluate --dataset outputs/demo_suite --models blind_prior,pixel_heuristic,ollama:qwen2.5vl:3b,gemini:gemini-3.5-flash-lite,oracle

# 7. Launch Interactive Studio UI 2.0 at http://127.0.0.1:8000 (HTML report at /report)
vtf serve --dataset samples/demo_suite --port 8000
```

### Run Full Automated Tests
```bash
pytest -v
```
