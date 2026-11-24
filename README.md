# Visual Task Factory (Innodata AI Hackathon — Challenge 02)

A **reusable, Dockerized, deterministic visual evaluation factory** that synthetically generates diverse multimodal visual reasoning tasks, enforces a **5-gate automated validation pipeline** (verified via **mutation testing**), generates **counterfactual visual twin pairs**, and benchmarks multimodal AI models across failure modes.

---

## Submission Deliverables Map (Official Spec Aligned)

| Official Requirement | Included Location |
|---|---|
| **Runnable Source Code & Setup** | [src/vtf/](src/vtf/), [Dockerfile](Dockerfile), [pyproject.toml](pyproject.toml) |
| **Sample Outputs & Findings** | [samples/demo_suite/](samples/demo_suite/) (tasks, PNGs, `benchmark_report.md`) |
| **Validation & Mutation Evidence** | [tests/](tests/), [samples/demo_suite/mutation_report.json](samples/demo_suite/mutation_report.json), `vtf validate`, `vtf mutate` |
| **Technical Explanation** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PITCH_OUTLINE.md](docs/PITCH_OUTLINE.md) |
| **Demo Walkthrough Script** | [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) |

---

## Key Features & Engineering Highlights

### 1. Meaningful Variation Across 4 Visual Families × 3 Difficulty Tiers
| Family | Subtypes | Visual & Reasoning Challenges |
|---|---|---|
| **`charts`** | Vertical bar, Horizontal bar, Grouped bar, Line series, Stacked bar, Dual-axis combo | Extrema, threshold counting, series differences, net growth, stacked totals, dual-axis conditional filtering, unlabeled axis reading |
| **`spatial_inventory`** | Warehouse storage racks, CLEVR-inspired compositional geometric scenes | Attribute-filtered counting, inventory summing, left/right spatial anchors, pattern recognition, z-order occlusion depth |
| **`logic_circuits`** | Multi-stage Boolean schematics (`AND`, `OR`, `XOR`, `NAND`, `NOR`, `NOT`), Directed open/blocked flow graphs | Signal tracing along orthogonal wires, single-pin fault sensitivity, Dijkstra shortest path over open edges |
| **`structured_docs`** | Enterprise purchase invoices, Hardware QA inspection matrices | Cell lookup, drawn checkbox filtering, cross-column arithmetic discrepancy auditing (`Qty × Unit Price != Printed Total`) |

### 2. Five-Gate Automated Task Validator (`src/vtf/validator.py`)
Every generated task passes five independent checks before entering the suite:
1. **`image_integrity_and_bounds`**: Verifies image dimensions and ensures all rendered elements lie strictly within `[0, W] × [0, H]`.
2. **`visual_readability_and_overlap`**: Enforces minimum queried font sizes and detects overlapping text/tick labels using actual rendered pixel bounding boxes (`matplotlib` renderer extents & `Pillow` geometry). Also verifies controlled occlusion ranges `[5%, 72%]` on depth-ordering tasks.
3. **`strict_qa_grounding`**: Ensures every referenced entity and answer evidence ID is present in `SceneManifest` and visibly rendered.
4. **`independent_solver_verification`**: Re-computes the exact ground-truth answer independently from the canonical JSON spec and records a step-by-step `solver_trace`.
5. **`anti_shortcut_leakage_audit`**: Rejects verbatim answer leakage in questions and tracks blind text-only guessing priors.

### 3. Mutation Testing (`vtf mutate`)
Proves the validator and answer scorer catch deliberately injected faults (clipped bboxes, mismatched image dims, overlapping labels, tiny fonts, missing/hidden evidence IDs, corrupted answers, verbatim leaks, and wrong numeric predictions) with a **100% kill rate (9/9 mutants killed)**.

### 4. Counterfactual Visual Twin Pairs (`*_cf`) & Pluggable VLM Harness
- Every base task can generate a **minimal visual twin** that flips the verified answer.
- Supports **Google Gemini** (`gemini:gemini-3.6-flash`), **OpenAI / OpenRouter / Groq** (`openai:...`, `openrouter:...`, `groq:...`), **Local Ollama Vision** (`ollama:qwen2.5vl:3b` / `ollama:moondream`), and built-in **offline diagnostic baselines** (`blind_prior`, `pixel_heuristic`, `oracle`).

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
# 1. Generate a repeatable validated suite (48 tasks = 24 base + 24 counterfactual twins)
vtf generate --out outputs/demo_suite --per-cell 2 --seed 42

# 2. Verify all 5 validation gates pass on the suite
vtf validate --dataset outputs/demo_suite

# 3. Run mutation testing to verify fault detection
vtf mutate --out outputs/demo_suite/mutation_report.json

# 4. Benchmark offline baselines (proves zero text-only cheating + 100% solvability)
vtf evaluate --dataset outputs/demo_suite --models blind_prior,pixel_heuristic,oracle

# 5. Benchmark a real local Ollama Vision model (after: `ollama pull qwen2.5vl:3b`)
vtf evaluate --dataset outputs/demo_suite --models blind_prior,ollama:qwen2.5vl:3b

# 6. Benchmark Google Gemini (after setting GEMINI_API_KEY)
vtf evaluate --dataset outputs/demo_suite --models blind_prior,gemini:gemini-3.6-flash

# 7. Launch Interactive Studio UI at http://127.0.0.1:8000
vtf serve --dataset samples/demo_suite --port 8000
```

### Run Full Automated Tests
```bash
pytest -v
```
