# Validation & Mutation Evidence Summary

All checks below were executed directly against the repository after final edits.

## 1. Automated Unit, E2E & Grounding Test Suite (`pytest -v`)
- **Result:** `19 passed`
- **Covered Suites:**
  - `tests/test_determinism.py`: Byte-identical PNG SHA-256 hashes, specs, and bounding-box manifests across repeated seeds for all 4 families.
  - `tests/test_families.py`: All 4 families (`charts`, `spatial_inventory`, `logic_circuits`, `structured_docs`) × 3 difficulties (`easy`, `medium`, `hard`) + counterfactual twin answer-flipping validation (`12` parameterized tests).
  - `tests/test_validator.py`: Verifies 5-gate rejection on out-of-bounds elements, ungrounded question references, verbatim answer leaks, and overlapping tick labels.
  - `tests/test_scoring.py`: Verifies JSON, `<answer>`, currency, numeric tolerance, string, and boolean extraction/scoring.
  - `tests/test_mutations.py`: Verifies `9/9` fault-injection mutants killed (`100%` kill rate).
  - `tests/test_pipeline_e2e.py`: Full batch generation → validation → offline benchmark → FastAPI Studio endpoint checks.

## 2. Five-Gate Validator (`vtf validate --dataset samples/demo_suite`)
- **Valid Tasks:** `24 / 24 passed` (`0` failed, `100%` grounding coverage).
- **Counterfactual Twin Pairs:** `12` pairs (`12` base + `12` counterfactual twins) where every twin changes a single visual fact and flips the verified answer.

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

## 4. Live Multimodal Benchmark Findings (`samples/demo_suite/benchmark_report.md`)
- `blind_text_prior` (no image): **8.3%** overall (**0.0%** counterfactual consistency) — proves tasks cannot be cheated from text priors alone.
- `pixel_cv_heuristic`: **12.5%** overall (**0.0%** counterfactual consistency) — proves naive pixel statistics fail.
- `gemini-3.5-flash-lite`: **83.3%** overall (**83.3%** counterfactual consistency; 0 API errors) — **100%** on Charts, Spatial/Occlusion & Invoices/QA, dropping to **33.3%** on `logic_circuits` (failed 4-input schematic tracing & constrained shortest-path DAG).
- `gemini-3-flash-preview`: **91.7%** overall (**91.7%** counterfactual consistency) — **100% (22/22)** across all answered tasks including `logic_circuits`, with the final 2 calls (`structured_docs_hard_s383` and `_cf`) hitting free-tier `429` daily quota (`2` API errors).
- `oracle_spec_verifier`: **100.0%** overall (**100.0%** counterfactual consistency) — confirms 100% deterministic solvability.
