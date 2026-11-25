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
  - **5-Gate Automated Validator + Mutation Testing + Blind LLM Audit:** Guarantees every queried object and answer is visibly grounded inside the image (`100%` grounding coverage, `9/9` fault-injection mutation kill rate), and verifies via `vtf audit-blind` that an image-less local Ollama `mistral:latest` 7B model cannot solve tasks.
  - **Counterfactual Visual Pairs (`*_cf`) & Redacted Abstention:** Flips a single visual fact per pair (`blind_text_prior`: `10.0%`, `blind_llm_mistral_latest`: `0.0%` overall & `0.0%` counterfactual consistency) and includes black-redacted evidence audits expecting `CANNOT_DETERMINE` (`hallucination_rate`).

---

## Slide 4 — List of Features Offered by the Solution
*(Insert image: `docs/assets/families_showcase.png`)*
- **5 Distinct Visual Families × 3 Difficulty Tiers (`samples/demo_suite` = 30 validated tasks = 15 unique pairs):**
  1. `charts`: Vertical/horizontal, grouped, unlabeled OCR-proof visual gap comparison, line, stacked, and dual-axis bar+line combo charts.
  2. `spatial_inventory`: Warehouse inventory racks + CLEVR-style compositional shapes with controlled z-order occlusion.
  3. `logic_circuits`: Dense 5-input boolean schematics with semicircular crossing bridge arcs (`circuit_fault_sensitivity`) & directed open/blocked flow DAGs.
  4. `structured_docs`: Invoice ledgers (drawn checkboxes, arithmetic discrepancy audit), redacted `CANNOT_DETERMINE` abstention tests, & hardware QA inspection matrices.
  5. `blueprints_gauges`: Architectural floorplans (`blueprint_area_sum`, doorway shortest-path `blueprint_door_hops`) & industrial analog needle dial gauge clusters (`gauge_danger_zone_count`, `analog_needle_reading`).
- **Integrated Evaluation & Studio UI 2.0:** Resumable JSONL prediction cache, standalone `benchmark_report.html`, `blind_prior`, `pixel_cv_heuristic`, `ollama_blind:mistral:latest`, `oracle`, plus Gemini / OpenAI / OpenRouter / Ollama Vision adapters, and FastAPI Studio 2.0 (`VLM Failures Only` filter, Side-by-Side Twin diff, SVG grounding overlay, and Per-Model response logs).

---

## Slide 5 — Process Flow Diagram / Use-Case Diagram
*(Insert images: `docs/assets/model_failure_breakdown.png` & `docs/assets/failure_spotlight.png`)*
- **End-to-End Flow:**
  1. Select `(family, difficulty, seed)` → generate canonical JSON spec across 15 unique visual reasoning types.
  2. Render image + exact `SceneManifest` pixel bounding boxes & independently compute verified answer + `solver_trace`.
  3. Filter through **5 Validation Gates** (bounds, overlap/readability, strict Q/A grounding, independent solver cross-check, anti-shortcut leakage) + generate counterfactual twin `*_cf`.
  4. Benchmark multimodal VLMs & blind audits with resumable caching → emit `Accuracy × Family × Difficulty`, Counterfactual Consistency, Hallucination Rate, and standalone MD/JSON/HTML reports.
- **Key Empirical Findings (`samples/demo_suite`, 30 tasks):**
  - `blind_text_prior` / `pixel_cv_heuristic`: **10.0%** / **6.7%** overall (**0.0%** counterfactual consistency).
  - `blind_llm_mistral_latest` (local Ollama `mistral:latest` 7B without images): **0.0%** overall (**0/30**, **0.0%** counterfactual consistency) — live LLM proof of zero text-only cheating.
  - `gemini-3.5-flash-lite` (`30/30`, **0 API errors**): **83.3%** overall (**73.3%** CF consistency, **0.0%** hallucination rate on abstention), acing Charts, Spatial & Redacted Docs (`100%`), while struggling on Blueprint doorway hops (`66.7%`) & Circuits (`50.0%`).
  - `gemini-3.5-flash`: **70.0%** overall (**21/22 = 95.5%** on valid calls before hitting free-tier `429` daily cap on #23–30; solved medium Circuits/DAGs yet STILL failed dense 5-pin crossing schematic `logic_circuits_hard_s294_cf`, predicting `B` instead of `E`).

---

## Slide 6 — Wireframes / Mock Diagrams (Studio UI 2.0 Screenshot)
*(Ready-to-use live capture saved at: `docs/assets/studio_ui_screenshot.png`)*
- Highlights:
  - Interactive **Live Generate + 5-Gate Validate** sidebar + **Family / Difficulty / VLM Failures Only** filters.
  - **Side-by-Side Counterfactual Twin** view + **SVG Grounding Box Overlay** highlighting referenced primitives (blue) and answer evidence (green).
  - **Per-Model Evaluation Responses** card + **Benchmark Summary Table** (including `Hallucination` and `Blueprints` columns).

---

## Slide 7 — Architecture Diagram of the Proposed Solution
*(Insert image: `docs/assets/architecture_diagram.png`)*
- Modular Python package (`src/vtf/`) separating `families/` (5 modules), `validator.py`, `factory.py`, `scoring.py`, `evaluators.py`, `benchmark.py`, `mutation.py`, `assets.py`, `deck.py`, and `server.py`.

---

## Slide 8 — Technologies Used in the Solution
- **Core Pipeline:** Python 3.12, Pydantic v2, Matplotlib (Agg renderer extents), Pillow (5-pin bridge schematics, floorplans, dial gauges, bundled TrueType typography), NumPy.
- **API & Interactive Studio 2.0:** FastAPI, Uvicorn, HTTPX, HTML5/SVG Grounding Overlay, standalone HTML report generator.
- **Model Adapters & Blind LLM Audit:** Google Gemini REST, OpenAI-compatible Vision APIs (OpenAI / OpenRouter / Groq), Local Ollama Vision & Text Blind Auditor (`ollama_blind:mistral:latest`).
- **Verification & CI:** `pytest` (`22/22` tests), 9-mutant Fault-Injection Suite (`vtf mutate`), `.github/workflows/ci.yml`, and **Docker** (`Dockerfile`).

---

## Slide 9 — Estimated Implementation Cost
- **Pipeline, Blind LLM Audit & Verification Cost:** **$0** — synthesis, 5-gate validation, mutation testing, counterfactual twins, and local Ollama `mistral:latest` blind auditing run 100% on local CPU/GPU.
- **Model Evaluation Cost:** **$0** during prototyping via free Google AI Studio tier and local Ollama; resumable `predictions_cache.jsonl` avoids re-paying completed calls when scaling with finalist credits.

---

## Slide 10 — Hackathon Deliverables Checklist
- **Runnable Source Code, Docker & CI:** `https://github.com/anishkarak4-ux/NitroKnight` (includes `Dockerfile`, `.github/workflows/ci.yml`, `pyproject.toml`, `README.md`).
- **Sample Outputs:** Committed under `samples/demo_suite/` (30 validated PNG tasks, JSONL specs, manifests, `benchmark_report.{md,json,html}`, and `predictions_cache.jsonl`).
- **Validation Evidence:** `pytest` suite (`22/22` pass), `vtf validate` (`30/30`), `samples/demo_suite/mutation_report.json` (`9/9` killed), and live benchmark results contrasting blind priors (`10.0%` / `0.0%`) vs Gemini (`83.3%` Flash-Lite / `21/22` valid Flash) vs Oracle (`100%`).
- **Technical Explanation & Live Demo:** `docs/ARCHITECTURE.md` + 3–4 minute walkthrough video (`docs/DEMO_SCRIPT.md`).

---

## Slide 11 — Thank You
- Add team contact info, GitHub link (`https://github.com/anishkarak4-ux/NitroKnight`), and demo video link.
