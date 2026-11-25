# Validation & Mutation Evidence Summary

All checks below were executed directly against the repository after final edits.

## 1. Automated Unit, E2E & Grounding Test Suite (`pytest -v`)
- **Result:** `25 passed` (enforced on every push via `.github/workflows/ci.yml` Python `verify` + `docker` build/run jobs)
- **Covered Suites:**
  - `tests/test_determinism.py`: Byte-identical PNG SHA-256 hashes, specs, and bounding-box manifests across repeated seeds for all 5 families.
  - `tests/test_families.py`: All 5 families (`charts`, `spatial_inventory`, `logic_circuits`, `structured_docs`, `blueprints_gauges`) × 3 difficulties (`easy`, `medium`, `hard`) + counterfactual twin answer-flipping validation (`15` parameterized tests).
  - `tests/test_validator.py`: Verifies 5-gate rejection on out-of-bounds elements, ungrounded question references, verbatim answer leaks, and overlapping tick labels.
  - `tests/test_scoring.py`: Verifies JSON, `<answer>`, currency, numeric tolerance, `CANNOT_DETERMINE` abstention handling, string, and boolean extraction/scoring.
  - `tests/test_mutations.py`: Verifies `9/9` fault-injection mutants killed (`100%` kill rate).
  - `tests/test_perturbations_and_scale.py`: Verifies `scan_tilt` & `low_contrast_jpeg` bbox-preserving perturbations, zero-collision scale batches, and `attempted_accuracy` separation.
  - `tests/test_pipeline_e2e.py`: Full 30-task generation → validation → cached benchmark (Wilson 95% CI & error taxonomy) → FastAPI Studio (`/`, `/report`, `/images/*`, `/api/evaluate-one`) checks.

## 2. Five-Gate Validator (`vtf validate`) & 150-Task Scale Proof (`vtf stress-test`)
- **Showcase Suite Valid Tasks:** `30 / 30 passed` (`0` failed, `100%` grounding coverage, `15` unique counterfactual pairs).
- **150-Task Scale Telemetry (`samples/demo_suite/scale_report.json`):** Executed via `vtf stress-test --per-cell 5 --seed 100`: **`150 / 150 valid tasks`** (`75` counterfactual pairs), **`0` rejected candidates (`100%` pass rate)**, **`150 / 150` unique PNG SHA-256 hashes (`0` collisions)** in **`9.161s` (`16.37 tasks/sec`)**.

## 3. Mutation Testing Report (`samples/demo_suite/mutation_report.json`)
Executed via `vtf mutate`: **9 / 9 injected mutants killed (100% fault detection)**.

| Mutant Injected | Detector Gate | Killed |
|---|---|---|
| `clipped_element_bbox` | `image_integrity_and_bounds` | Yes |
| `mismatched_image_dimensions` | `image_integrity_and_bounds` | Yes |
| `overlapping_queried_labels` | `visual_readability_and_overlap` | Yes |
| `tiny_unreadable_font` | `visual_readability_and_overlap` | Yes |
| `ungrounded_question_entity` | `strict_qa_grounding` | Yes |
| `hidden_referenced_element` | `strict_qa_grounding` | Yes |
| `corrupted_ground_truth_answer` | `independent_solver_verification` | Yes |
| `verbatim_answer_leakage` | `anti_shortcut_leakage_audit` | Yes |
| `scorer_rejects_wrong_numeric` | `verify_prediction` | Yes |

## 4. Seven-Model Blind LLM, Local VLM, Frontier VLM & Perturbation Findings
From [samples/demo_suite/benchmark_report.md](file:///c:/Users/KIIT/Desktop/NitroKnight/samples/demo_suite/benchmark_report.md):
- `blind_text_prior` (no image): **10.0%** (`3/30`, Wilson 95% CI `[3.5%, 25.6%]`, **0.0%** CF consistency).
- `pixel_cv_heuristic`: **6.7%** (`2/30`, Wilson 95% CI `[1.8%, 21.3%]`, **0.0%** CF consistency).
- `blind_llm_mistral_latest` (local Ollama `mistral:latest` 7B without images): **0.0%** (`0/30`, Wilson 95% CI `[0.0%, 11.3%]`, **0.0%** CF consistency) — proves non-shortcuttability against real LLMs.
- `qwen2.5vl:3b` (open-weights local 3B VLM via Ollama, `0` API errors): **56.7%** (`17/30`, Wilson 95% CI `[39.2%, 72.6%]`, **46.7%** CF consistency, **0.0%** hallucination rate) — aced `charts` (**100.0%**) and redacted abstention, while failing `spatial_inventory` (**50.0%**), `logic_circuits` (**33.3%**), and `blueprints_gauges` (**33.3%**).
- `gemini-3.5-flash-lite` (`30/30`, `0` API errors): **83.3%** (`25/30`, Wilson 95% CI `[66.4%, 92.7%]`, **73.3%** CF consistency, **0.0%** hallucination rate) — **100%** on Charts, Spatial & Docs, dropping to **66.7%** on `blueprints_gauges` and **50.0%** on `logic_circuits`.
- `gemini-3.5-flash`: **70.0%** strict / **95.5% attempted (`21/22`)** (Wilson 95% CI `[78.2%, 99.2%]`, **66.7%** CF consistency; final `8` tasks #23–30 hit free-tier `429` quota cap) — solved Flash-Lite's medium DAG/circuits, yet STILL **failed** 5-pin crossing schematic `logic_circuits_hard_s294_cf` (`B` vs `E`). Notice **all 3 real VLMs failed `s294_cf`** (`qwen2.5vl:3b -> D`, `flash-lite -> C`, `flash -> B`).
- `oracle_spec_verifier`: **100.0%** (`30/30`, Wilson 95% CI `[88.6%, 100.0%]`, **100.0%** CF consistency, **0.0%** hallucination rate).
- **Perturbation Robustness Sweep ([robustness_report.json](file:///c:/Users/KIIT/Desktop/NitroKnight/samples/demo_suite/robustness_report.json), `gemini-3.5-flash-lite`, `N=10` stratified):** Clean **70.0%** (`7/10`) → Scan Tilt (`±2°`, JPEG 76) **70.0%** (`7/10`) → Low-Contrast Sensor Noise (JPEG 38) **60.0%** (`6/10`, CI `[31.3%, 83.2%]`).
