# Visual Task Factory — Evaluation & Validation Report

- **Dataset:** `samples\demo_suite`
- **Valid Tasks:** `30` (Rejected invalid candidates: `0`)
- **Models Evaluated:** `blind_text_prior`, `pixel_cv_heuristic`, `blind_llm_mistral_latest`, `qwen2.5vl:3b`, `gemini-3.5-flash-lite`, `gemini-3.5-flash`, `oracle_spec_verifier`

## 1. Overall & Attempted Accuracy (with 95% Wilson CI), Counterfactual Consistency & Hallucination

| Model | Strict Accuracy | Attempted Accuracy | 95% Wilson CI | CF Consistency | Hallucination Rate | API Errors |
|---|---:|---:|---:|---:|---:|---:|
| `blind_text_prior` | 10.0% | 10.0% (3/30) | [3.5%, 25.6%] | 0.0% | 100.0% | 0 |
| `pixel_cv_heuristic` | 6.7% | 6.7% (2/30) | [1.8%, 21.3%] | 0.0% | 100.0% | 0 |
| `blind_llm_mistral_latest` | 0.0% | 0.0% (0/30) | [0.0%, 11.3%] | 0.0% | 100.0% | 0 |
| `qwen2.5vl:3b` | 56.7% | 56.7% (17/30) | [39.2%, 72.6%] | 46.7% | 0.0% | 0 |
| `gemini-3.5-flash-lite` | 83.3% | 83.3% (25/30) | [66.4%, 92.7%] | 73.3% | 0.0% | 0 |
| `gemini-3.5-flash` | 70.0% | 95.5% (21/22) | [78.2%, 99.2%] | 66.7% | 0.0% | 8 |
| `oracle_spec_verifier` | 100.0% | 100.0% (30/30) | [88.6%, 100.0%] | 100.0% | 0.0% | 0 |

## 2. Breakdown by Visual Family

| Model | blueprints_gauges | charts | logic_circuits | spatial_inventory | structured_docs |
|---|---:|---:|---:|---:|---:|
| `blind_text_prior` | 0.0% | 16.7% | 33.3% | 0.0% | 0.0% |
| `pixel_cv_heuristic` | 0.0% | 16.7% | 16.7% | 0.0% | 0.0% |
| `blind_llm_mistral_latest` | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| `qwen2.5vl:3b` | 33.3% | 100.0% | 33.3% | 50.0% | 66.7% |
| `gemini-3.5-flash-lite` | 66.7% | 100.0% | 50.0% | 100.0% | 100.0% |
| `gemini-3.5-flash` | 0.0% | 100.0% | 83.3% | 100.0% | 66.7% |
| `oracle_spec_verifier` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## 3. Breakdown by Difficulty

| Model | Easy | Medium | Hard |
|---|---:|---:|---:|
| `blind_text_prior` | 10.0% | 10.0% | 10.0% |
| `pixel_cv_heuristic` | 10.0% | 10.0% | 0.0% |
| `blind_llm_mistral_latest` | 0.0% | 0.0% | 0.0% |
| `qwen2.5vl:3b` | 90.0% | 20.0% | 60.0% |
| `gemini-3.5-flash-lite` | 90.0% | 70.0% | 90.0% |
| `gemini-3.5-flash` | 80.0% | 80.0% | 50.0% |
| `oracle_spec_verifier` | 100.0% | 100.0% | 100.0% |

## 4. Failure Taxonomy Counts

| Model | abstention_hallucination | api_quota_error | blueprint_gauge_spatial | circuit_dag_reasoning | correct | numeric_mismatch | parse_failure | wrong_entity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `blind_text_prior` | 1 | 0 | 6 | 4 | 3 | 7 | 0 | 9 |
| `pixel_cv_heuristic` | 1 | 0 | 6 | 5 | 2 | 7 | 0 | 9 |
| `blind_llm_mistral_latest` | 1 | 0 | 6 | 6 | 0 | 0 | 8 | 9 |
| `qwen2.5vl:3b` | 0 | 0 | 4 | 4 | 17 | 2 | 0 | 3 |
| `gemini-3.5-flash-lite` | 0 | 0 | 2 | 3 | 25 | 0 | 0 | 0 |
| `gemini-3.5-flash` | 0 | 8 | 0 | 1 | 21 | 0 | 0 | 0 |
| `oracle_spec_verifier` | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 |
