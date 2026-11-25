# Visual Task Factory — Evaluation & Validation Report

- **Dataset:** `samples\demo_suite`
- **Valid Tasks:** `30` (Rejected invalid candidates: `0`)
- **Models Evaluated:** `blind_text_prior`, `pixel_cv_heuristic`, `blind_llm_mistral_latest`, `gemini-3.5-flash-lite`, `gemini-3.5-flash`, `oracle_spec_verifier`

## 1. Overall Accuracy, Counterfactual Consistency & Hallucination Rate

| Model | Overall Accuracy | Counterfactual Consistency | Hallucination Rate | API Errors |
|---|---:|---:|---:|---:|
| `blind_text_prior` | 10.0% | 0.0% | 100.0% | 0 |
| `pixel_cv_heuristic` | 6.7% | 0.0% | 100.0% | 0 |
| `blind_llm_mistral_latest` | 0.0% | 0.0% | 100.0% | 0 |
| `gemini-3.5-flash-lite` | 83.3% | 73.3% | 0.0% | 0 |
| `gemini-3.5-flash` | 70.0% | 66.7% | 0.0% | 8 |
| `oracle_spec_verifier` | 100.0% | 100.0% | 0.0% | 0 |

## 2. Breakdown by Visual Family

| Model | blueprints_gauges | charts | logic_circuits | spatial_inventory | structured_docs |
|---|---:|---:|---:|---:|---:|
| `blind_text_prior` | 0.0% | 16.7% | 33.3% | 0.0% | 0.0% |
| `pixel_cv_heuristic` | 0.0% | 16.7% | 16.7% | 0.0% | 0.0% |
| `blind_llm_mistral_latest` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| `gemini-3.5-flash-lite` | 66.7% | 100.0% | 50.0% | 100.0% | 100.0% |
| `gemini-3.5-flash` | 0.0% | 100.0% | 83.3% | 100.0% | 66.7% |
| `oracle_spec_verifier` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## 3. Breakdown by Difficulty

| Model | Easy | Medium | Hard |
|---|---:|---:|---:|
| `blind_text_prior` | 10.0% | 10.0% | 10.0% |
| `pixel_cv_heuristic` | 10.0% | 10.0% | 0.0% |
| `blind_llm_mistral_latest` | 0.0% | 0.0% | 0.0% |
| `gemini-3.5-flash-lite` | 90.0% | 70.0% | 90.0% |
| `gemini-3.5-flash` | 80.0% | 80.0% | 50.0% |
| `oracle_spec_verifier` | 100.0% | 100.0% | 100.0% |
