# Visual Task Factory — Evaluation & Validation Report

- **Dataset:** `samples\demo_suite`
- **Valid Tasks:** `24` (Rejected invalid candidates: `0`)
- **Models Evaluated:** `blind_text_prior`, `pixel_cv_heuristic`, `oracle_spec_verifier`

## 1. Overall Accuracy & Counterfactual Visual Consistency

| Model | Overall Accuracy | Counterfactual Consistency |
|---|---:|---:|
| `blind_text_prior` | 8.3% | 0.0% |
| `pixel_cv_heuristic` | 12.5% | 0.0% |
| `oracle_spec_verifier` | 100.0% | 100.0% |

## 2. Breakdown by Visual Family

| Model | charts | logic_circuits | spatial_inventory | structured_docs |
|---|---:|---:|---:|---:|
| `blind_text_prior` | 0.0% | 33.3% | 0.0% | 0.0% |
| `pixel_cv_heuristic` | 0.0% | 33.3% | 0.0% | 16.7% |
| `oracle_spec_verifier` | 100.0% | 100.0% | 100.0% | 100.0% |

## 3. Breakdown by Difficulty

| Model | Easy | Medium | Hard |
|---|---:|---:|---:|
| `blind_text_prior` | 12.5% | 12.5% | 0.0% |
| `pixel_cv_heuristic` | 12.5% | 25.0% | 0.0% |
| `oracle_spec_verifier` | 100.0% | 100.0% | 100.0% |
