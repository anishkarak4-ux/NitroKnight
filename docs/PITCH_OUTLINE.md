# Official Hack2skill Pitch Deck Guide (Exact 11-Slide Mapping)

Mapped 1-to-1 to your uploaded template: `docs/Innodata _ IDEA SUBMISSION - Google Slides.pdf`  
Make a copy of the Google Slides template, replace the placeholder text with each section below, and insert the generated visuals from `docs/assets/`.

> **Note on Track Clarity:** Per the official Innodata Participant Guide, `pallets/click`, `colinhacks/zod`, `jsoncpp`, and `Harbor v0.25.x` apply exclusively to **Track 1 (Coding Task Factory)**. Your team is submitting **Track 2 (Challenge 02: Visual Task Factory)**, which requires an automated synthetic visual task pipeline, verified answers, evaluation findings across model strengths/weaknesses, runnable Dockerized code, sample outputs, validation/mutation evidence, and a demo video.

---

## Slide 1 — Title Slide
- **Team Name:** `NitroKnight` *(or your registered Hack2skill team name)*
- **Team Leader Name:** `Anish Karak` *(add your 2 teammates' names if desired)*
- **Problem Statement:** `Challenge 02 — Visual Task Factory`

---

## Slide 2 — Brief about the Idea
- **Visual Task Factory (VTF)** is a deterministic, spec-first synthetic data and evaluation engine that generates diverse visual reasoning tasks, independently verifies every question and answer directly against pixel-level layout manifests, and diagnoses where multimodal AI models succeed or fail.
- Instead of static or LLM-guessed benchmarks, VTF converts seeded JSON world specifications into PNG images, pixel bounding boxes, symbolic ground-truth solutions, **counterfactual visual twin pairs**, and quantitative model diagnostics.

---

## Slide 3 — Opportunity & USP
- **Why existing benchmarks fall short:** Public datasets (`ChartQA`, `VQA v2`, `CLEVR`) suffer from training-data memorization and text-only language priors where models guess answers without inspecting the image.
- **How our factory solves it & USP:**
  - **Spec-First Truth (Zero Diffusion Hallucination):** Renders PNGs programmatically from structured specs so numeric/spatial ground truth is 100% mathematically exact.
  - **5-Gate Automated Validator + Mutation Testing:** Guarantees every queried object and answer is visibly grounded inside the image (`100%` grounding coverage, `9/9` fault-injection mutation kill rate).
  - **Counterfactual Visual Pairs (`*_cf`):** Flips a single visual fact per pair to catch models guessing from language priors (`blind_text_prior`: `8.3%` accuracy, `0.0%` counterfactual consistency).

---

## Slide 4 — List of Features Offered by the Solution
*(Insert image: `docs/assets/families_showcase.png`)*
- **4 Distinct Visual Families × 3 Difficulty Tiers:**
  1. `charts`: Vertical/horizontal, grouped (with unlabeled axis-reading), line, stacked, and dual-axis bar+line combo charts.
  2. `spatial_inventory`: Warehouse inventory racks + CLEVR-style compositional shapes with controlled z-order occlusion.
  3. `logic_circuits`: Multi-stage boolean gate schematics (`AND/OR/XOR/NAND/NOR/NOT`, fault sensitivity) & open/blocked flow DAGs.
  4. `structured_docs`: Invoice ledgers (drawn checkboxes, arithmetic discrepancy audit) & hardware QA inspection matrices.
- **Integrated Evaluation & Studio UI:** Automated test runner (`blind_prior`, `pixel_cv_heuristic`, `oracle`, plus Gemini / OpenAI / OpenRouter / local Ollama Vision) + FastAPI Studio with live SVG bounding-box grounding overlays.

---

## Slide 5 — Process Flow Diagram / Use-Case Diagram
*(Insert image: `docs/assets/model_failure_breakdown.png` or `docs/assets/validation_and_baselines.png`)*
- **End-to-End Flow:**
  1. Select `(family, difficulty, seed)` → generate canonical JSON spec.
  2. Render image + exact `SceneManifest` pixel bounding boxes & independently compute verified answer + `solver_trace`.
  3. Filter through **5 Validation Gates** (bounds, overlap/readability, strict Q/A grounding, independent solver cross-check, anti-shortcut leakage) + generate counterfactual twin `*_cf`.
  4. Benchmark multimodal VLMs & baselines → emit accuracy breakdown (`Family × Difficulty × Reasoning`) + Counterfactual Consistency report.
- **Key Empirical Findings (`samples/demo_suite`, 24 tasks):**
  - `blind_text_prior`: **8.3%** overall (**0.0%** counterfactual consistency) — proves tasks cannot be cheated without pixels.
  - `gemini-3.5-flash-lite`: **83.3%** overall (**100%** on Charts, Spatial/Occlusion, and Invoices/QA, dropping to **33.3%** on Logic Schematics & Flow Networks).
  - `gemini-3-flash-preview`: **91.7%** overall (**100%** across all **22/22** completed calls including Logic & Flow; final 2 tasks hit free-tier 429 quota).

---

## Slide 6 — Wireframes / Mock Diagrams (Studio UI Screenshot)
*(Ready-to-use live capture saved at: `docs/assets/studio_ui_screenshot.png`)*
- Highlights:
  - Interactive **Live Generate + 5-Gate Validate** sidebar.
  - **SVG Grounding Box Overlay** highlighting referenced primitives (blue) and answer evidence (green) directly over pixels.
  - Live **Independent Symbolic Solver Trace** and **Benchmark Summary Table**.

---

## Slide 7 — Architecture Diagram of the Proposed Solution
*(Insert image: `docs/assets/architecture_diagram.png`)*
- Modular Python package (`src/vtf/`) separating `families/`, `validator.py`, `factory.py`, `scoring.py`, `evaluators.py`, `benchmark.py`, `mutation.py`, and `server.py`.

---

## Slide 8 — Technologies Used in the Solution
- **Core Pipeline:** Python 3.12, Pydantic v2, Matplotlib (Agg renderer extents), Pillow (deterministic vector-style rendering & bundled TrueType typography), NumPy.
- **API & Interactive Studio:** FastAPI, Uvicorn, HTTPX, HTML5/SVG Grounding Overlay.
- **Model Adapters:** Google Gemini API (`google-genai` / REST), OpenAI-compatible Vision APIs (OpenAI / OpenRouter / Groq), Local Ollama Vision (`qwen2.5vl:3b` / `moondream`).
- **Verification & Reproducibility:** `pytest`, 9-mutant Fault-Injection Suite (`vtf mutate`), and **Docker** (`Dockerfile` for standardized judge execution).

---

## Slide 9 — Estimated Implementation Cost
- **Pipeline & Verification Cost:** **$0** — synthesis, 5-gate validation, mutation testing, counterfactual generation, and offline diagnostic baselines run 100% deterministically on local CPU.
- **Model Evaluation Cost:** **$0** during prototyping via local **Ollama** vision models (`qwen2.5vl:3b` / `moondream`) or free-tier Google AI Studio Gemini API quotas; scalable to frontier models using finalist credits.

---

## Slide 10 — Hackathon Deliverables Checklist
- **Runnable Source Code + Docker:** `https://github.com/anishkarak4-ux/NitroKnight` (includes `Dockerfile`, `pyproject.toml`, `README.md`).
- **Sample Outputs:** Committed under `samples/demo_suite/` (24+ validated PNG tasks, JSONL specs, grounding manifests, and benchmark reports).
- **Validation Evidence:** `pytest` suite (`100%` pass), `vtf validate`, `samples/demo_suite/mutation_report.json` (`9/9` injected faults killed), and live benchmark results (`8.3%` blind vs `83.3%` `gemini-3.5-flash-lite` vs `91.7%` `gemini-3-flash-preview` vs `100%` oracle).
- **Technical Explanation & Live Demo:** `docs/ARCHITECTURE.md` + 3–4 minute walkthrough video (`docs/DEMO_SCRIPT.md`).

---

## Slide 11 — Thank You
- Add team contact info, GitHub link (`https://github.com/anishkarak4-ux/NitroKnight`), and demo video link.
