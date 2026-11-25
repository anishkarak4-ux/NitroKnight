# Validation & Mutation Evidence Summary

All checks below were executed directly against the repository after final edits.

## 1. Automated Unit, E2E & Grounding Test Suite (`pytest -v`)
- **Result:** `22 passed` (enforced on every push via `.github/workflows/ci.yml`)
- **Covered Suites:**
  - `tests/test_determinism.py`: Byte-identical PNG SHA-256 hashes, specs, and bounding-box manifests across repeated seeds for all 5 families.
  - `tests/test_families.py`: All 5 families (`charts`, `spatial_inventory`, `logic_circuits`, `structured_docs`, `blueprints_gauges`) × 3 difficulties (`easy`, `medium`, `hard`) + counterfactual twin answer-flipping validation (`15` parameterized tests).
  - `tests/test_validator.py`: Verifies 5-gate rejection on out-of-bounds elements, ungrounded question references, verbatim answer leaks, and overlapping tick labels.
  - `tests/test_scoring.py`: Verifies JSON, `<answer>`, currency, numeric tolerance, `CANNOT_DETERMINE` abstention handling, string, and boolean extraction/scoring.
  - `tests/test_mutations.py`: Verifies `9/9` fault-injection mutants killed (`100%` kill rate).
  - `tests/test_pipeline_e2e.py`: Full 30-task generation → validation → offline benchmark + resumable `predictions_cache.jsonl` + HTML report → FastAPI Studio 2.0 endpoint checks.

## 2. Five-Gate Validator (`vtf validate --dataset samples/demo_suite`)
- **Valid Tasks:** `30 / 30 passed` (`0` failed, `100%` grounding coverage).
- **Counterfactual Twin Pairs:** `15` pairs (`15` base across unique reasoning types + `15` counterfactual twins) where every twin changes a single visual fact and flips the verified answer.

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

## 4. Live Blind LLM & Multimodal Benchmark Findings (`samples/demo_suite/benchmark_report.md`)
- `blind_text_prior` (no image): **10.0%** overall (**0.0%** counterfactual consistency, **100.0%** hallucination rate on redacted audit) — proves tasks cannot be cheated from text regex priors alone.
- `pixel_cv_heuristic`: **6.7%** overall (**0.0%** counterfactual consistency) — proves naive pixel statistics fail.
- `blind_llm_mistral_latest` (local Ollama `mistral:latest` 7B receiving text question only): **0.0%** overall (**0/30**, **0.0%** counterfactual consistency, **100.0%** hallucination rate) — real-LLM proof that the dataset resists blind LLM guessing.
- `gemini-3.5-flash-lite`: **83.3%** overall (**25/30**, **73.3%** counterfactual consistency, **0.0%** hallucination rate on redacted `CANNOT_DETERMINE` audit; `0` API errors) — **100%** on Charts (including unlabeled gap reading), Spatial/Occlusion, and Structured Docs, dropping to **66.7%** on `blueprints_gauges` (failed floorplan doorway-hop path `s449` & `_cf`) and **50.0%** on `logic_circuits` (failed counterfactual schematic/DAG pairs).
- `gemini-3.5-flash`: **70.0%** overall (**21/22 = 95.5%** across non-errored calls; **66.7%** counterfactual consistency) — outscored Flash-Lite on `logic_circuits` (**83.3%**), solving the medium schematic/DAG problems, yet still **failed** dense 5-input crossing schematic `logic_circuits_hard_s294_cf` (predicting `B` instead of `E` across bridge arcs). Final `8` tasks (#23–30: `structured_docs_hard_*` & `blueprints_gauges_*`) hit Google AI Studio free-tier `429` daily quota (`8` API errors).
- `oracle_spec_verifier`: **100.0%** overall (**100.0%** counterfactual consistency, **0.0%** hallucination rate) — confirms 100% deterministic solvability.
