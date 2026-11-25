# Architecture & Engineering Design

## 1. Core Principle: Spec-First Deterministic Synthesis
Instead of using generative image diffusion models (which frequently hallucinate bar heights, text labels, and counts), **Visual Task Factory** synthesizes every task from a canonical JSON world specification:

```text
  [Seed + Config]
         │
         ▼
  1. Spec Generator ──────────► Canonical JSON Ground Truth (`ground_truth_spec`)
         │                              │
         ├──► 2. Renderer ────► PNG + Pixel `SceneManifest` (every bbox + occlusion)
         │                              │
         └──► 3. Symbolic Solver ───────┼──► Exact Answer + Step-by-Step `solver_trace`
                                        ▼
                            4. 5-Gate Validator
                      (Bounds, Overlap, Grounding, Re-Derivation, Anti-Shortcut)
                                        │
                      ┌─────────────────┴─────────────────┐
                      ▼                                   ▼
            [Valid TaskPackage]                [Rejected Candidate Log]
                      │
                      ├──► Counterfactual Twin (`*_cf`)
                      ▼
            5. Resumable VLM Evaluation Harness (Gemini / OpenAI / Ollama + Mistral Blind Audit)
                                        │
                                        ▼
       Accuracy + Counterfactual Consistency + Hallucination Rate (MD / JSON / HTML)
```

## 2. Why 5 Validation Gates + Blind LLM Audit?
1. **Bounds & Integrity**: Catches clipped chart legends, overflowing labels, or corrupt outputs.
2. **Readability & Anti-Overlap**: Uses actual Matplotlib `renderer` window extents and Pillow glyph bboxes to guarantee text labels remain legible.
3. **Strict Q/A Grounding**: Enforces that every referenced element ID exists in the rendered scene manifest and is not hidden/occluded past threshold.
4. **Independent Solver Cross-Check**: Re-computes the answer from `ground_truth_spec` independently and verifies exact type/value parity.
5. **Anti-Shortcut & Blind LLM Audit**: Flags prompt answer leakage, tracks deterministic guessing priors (`blind_text_prior`), and supports real image-less LLM auditing via `vtf audit-blind` (local Ollama `mistral:latest` -> `0.0%`).

## 3. Counterfactual Consistency & Hallucination Abstention
High benchmark accuracy alone can hide dataset shortcuts or fabricated guesses:
- **Counterfactual Consistency:** For each base task $T$, the factory synthesizes a minimally perturbed twin $T_{\text{cf}}$ where a single visual fact changes and flips the verified answer. A model passes **Counterfactual Consistency** on pair $(T, T_{\text{cf}})$ only if:
  - $\text{Correct}(T) = \text{True}$
  - $\text{Correct}(T_{\text{cf}}) = \text{True}$
  - $\text{Pred}(T) \neq \text{Pred}(T_{\text{cf}})$
- **Hallucination Abstention Rate:** Unanswerable redacted documents (`redacted_audit`) require emitting `CANNOT_DETERMINE` when evidence is black-masked (versus an exact dollar figure on the unredacted counterfactual twin), directly measuring grounded refusal vs hallucinated guessing.
