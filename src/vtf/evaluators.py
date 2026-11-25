"""Pluggable model evaluators for real VLMs and offline diagnostic baselines."""

from __future__ import annotations

import base64
import os
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image

from vtf.families import get_family
from vtf.schema import AnswerType, ModelPrediction, TaskPackage
from vtf.scoring import verify_prediction


def load_dotenv(path: Path | str = ".env") -> None:
    """Populate missing environment variables from a local .env file if present."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ and v:
            os.environ[k] = v


def build_vlm_prompt(task: TaskPackage) -> str:
    """Construct an unambiguous evaluation prompt for multimodal models."""
    type_hint = {
        AnswerType.INTEGER: "Return an exact integer.",
        AnswerType.NUMBER: "Return a single numeric value.",
        AnswerType.BOOLEAN: "Return true or false.",
        AnswerType.STRING: "Return the exact short name/code/value requested.",
    }[task.answer_type]
    return (
        "You are evaluating a visual reasoning task. Inspect the provided image carefully.\n"
        f"Question: {task.question}\n"
        f"Format requirement: {type_hint} "
        'Reply strictly with JSON: {"answer": <your_answer>, "reason": "<short visual evidence>"}.'
    )


class BaseEvaluator(ABC):
    """Common interface for VLM adapters and diagnostic baselines."""

    model_name: str
    provider: str
    uses_image: bool = True

    @abstractmethod
    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        """Return raw model text output for a single task."""

    def evaluate_task(self, task: TaskPackage, dataset_dir: Path) -> ModelPrediction:
        img_path = dataset_dir / task.image_path
        t0 = time.perf_counter()
        notes = ""
        try:
            raw = self.predict_raw(task, img_path)
            extracted, ok, score, err_cat = verify_prediction(
                raw, task.answer, task.answer_type, task.tolerance
            )
        except Exception as exc:  # noqa: BLE001
            raw = ""
            extracted = ""
            ok = False
            score = 0.0
            err_cat = "api_error"
            notes = str(exc)

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return ModelPrediction(
            task_id=task.task_id,
            model_name=self.model_name,
            provider=self.provider,
            raw_response=raw,
            extracted_answer=extracted,
            expected_answer=str(task.answer),
            correct=ok,
            score=score,
            error_category=err_cat,
            latency_ms=elapsed_ms,
            used_image=self.uses_image,
            notes=notes,
        )


class BlindTextPriorBaseline(BaseEvaluator):
    """Text-only diagnostic baseline (ignores image) to prove non-shortcuttability."""

    model_name = "blind_text_prior"
    provider = "diagnostic_baseline"
    uses_image = False

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        if task.answer_type == AnswerType.STRING:
            m = re.search(r"\(([^)]+)\s+vs\s+([^)]+)\)", task.question, flags=re.IGNORECASE)
            if m:
                return f'{{"answer": "{m.group(1).strip()}", "reason": "blind prior first option"}}'
            if task.reasoning_type == "circuit_fault_sensitivity":
                return '{"answer": "A", "reason": "blind prior guess"}'
            return '{"answer": "UNKNOWN", "reason": "cannot see image"}'
        if task.reasoning_type == "circuit_signal_tracing":
            return '{"answer": 0, "reason": "blind binary prior"}'
        return '{"answer": 0, "reason": "blind numeric prior"}'


class PixelHeuristicBaseline(BaseEvaluator):
    """Lightweight classic-CV pixel heuristic baseline (no OCR/VLM semantics)."""

    model_name = "pixel_cv_heuristic"
    provider = "diagnostic_baseline"
    uses_image = True

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        with Image.open(image_path) as im:
            arr = np.asarray(im.convert("RGB"))
        # Estimate dominant non-background chromatic area / simple fallback
        bg_mask = (arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235)
        fg_ratio = float((~bg_mask).mean())
        if task.answer_type == AnswerType.INTEGER:
            guess = max(1, int(round(fg_ratio * 20)))
            return f'{{"answer": {guess}, "reason": "foreground pixel ratio={fg_ratio:.3f}"}}'
        if task.answer_type == AnswerType.STRING:
            # Guess first category/color if mentioned in spec or generic placeholder
            if task.reasoning_type == "occlusion_depth_ordering":
                m = re.search(r"\(([^)]+)\s+vs\s+([^)]+)\)", task.question, flags=re.IGNORECASE)
                if m:
                    return f'{{"answer": "{m.group(2).strip()}", "reason": "pixel heuristic"}}'
            return '{"answer": "UNREADABLE_BY_PIXEL_HEURISTIC", "reason": "no semantic OCR/layout parsing"}'
        return '{"answer": 0, "reason": "pixel heuristic fallback"}'


class OracleVerifierBaseline(BaseEvaluator):
    """Symbolic upper-bound verifier reading canonical spec (sanity check = 100%)."""

    model_name = "oracle_spec_verifier"
    provider = "diagnostic_oracle"
    uses_image = False

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        fam = get_family(task.family)
        ans, *_ = fam.solve_spec(task.ground_truth_spec)
        return f'{{"answer": {json_escape(ans)}, "reason": "symbolic ground-truth solver"}}'


def json_escape(val: Any) -> str:
    import json

    return json.dumps(val)


class GeminiEvaluator(BaseEvaluator):
    """Google Gemini multimodal evaluator via Gemini REST API (supports free-tier keys)."""

    provider = "gemini"
    uses_image = True

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        api_key: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 5,
        min_delay_sec: float = 1.0,
    ) -> None:
        load_dotenv()
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_delay_sec = min_delay_sec
        if not self.api_key:
            raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY to run GeminiEvaluator.")

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": build_vlm_prompt(task)},
                        {"inline_data": {"mime_type": "image/png", "data": b64}},
                    ]
                }
            ]
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        data: dict[str, Any] = {}
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                if self.min_delay_sec > 0:
                    time.sleep(self.min_delay_sec)
                try:
                    resp = client.post(url, json=payload, headers=headers)
                except (httpx.TimeoutException, httpx.TransportError):
                    if attempt < self.max_retries:
                        time.sleep(min(20.0, 2.0 * (2**attempt)))
                        continue
                    raise
                if resp.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(min(25.0, 3.0 * (2**attempt)))
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)


class OpenAICompatibleEvaluator(BaseEvaluator):
    """Evaluator for OpenAI, OpenRouter, Groq, Together, or local vLLM vision models."""

    provider = "openai_compatible"
    uses_image = True

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 45.0,
    ) -> None:
        load_dotenv()
        self.model_name = model_name
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("GROQ_API_KEY")
        )
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("Set OPENAI_API_KEY / OPENROUTER_API_KEY / GROQ_API_KEY.")

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": build_vlm_prompt(task)},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return str(data["choices"][0]["message"]["content"])


class OllamaVisionEvaluator(BaseEvaluator):
    """Local Ollama multimodal vision evaluator (e.g., qwen2.5vl:3b, llama3.2-vision)."""

    provider = "ollama"
    uses_image = True

    def __init__(
        self,
        model_name: str = "qwen2.5vl:3b",
        host: str | None = None,
        timeout: float = 180.0,
    ) -> None:
        self.model_name = model_name
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": build_vlm_prompt(task),
                    "images": [b64],
                }
            ],
            "stream": False,
            "options": {"temperature": 0},
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return str(data["message"]["content"])


class OllamaTextBlindBaseline(BaseEvaluator):
    """Real text-only LLM audit (no image) via local Ollama to detect language-prior shortcuts."""

    provider = "blind_llm_audit"
    uses_image = False

    def __init__(
        self,
        model_name: str = "mistral:latest",
        host: str | None = None,
        timeout: float = 45.0,
    ) -> None:
        self.raw_model = model_name
        self.model_name = f"blind_llm_{model_name.replace(':', '_')}"
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout

    def predict_raw(self, task: TaskPackage, image_path: Path) -> str:
        prompt = (
            "You are answering a visual benchmark question WITHOUT seeing any image.\n"
            f"Question: {task.question}\n"
            'Try to guess the answer anyway, or reply UNKNOWN. Respond strictly in JSON: {"answer": <guess_or_UNKNOWN>}.'
        )
        payload = {
            "model": self.raw_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0},
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return str(data["message"]["content"])


def build_evaluator(spec: str) -> BaseEvaluator:
    """Factory helper from CLI model spec string.

    Examples:
        'blind_prior', 'pixel_heuristic', 'oracle',
        'ollama_blind:mistral:latest', 'gemini:gemini-3.5-flash-lite',
        'openai:gpt-4o', 'openrouter:google/gemini-2.5-flash', 'ollama:qwen2.5vl:3b'
    """
    if spec == "blind_prior":
        return BlindTextPriorBaseline()
    if spec == "pixel_heuristic":
        return PixelHeuristicBaseline()
    if spec == "oracle":
        return OracleVerifierBaseline()
    if spec.startswith("ollama_blind:"):
        return OllamaTextBlindBaseline(model_name=spec.split(":", 1)[1])
    if spec.startswith("gemini:"):
        return GeminiEvaluator(model_name=spec.split(":", 1)[1])
    if spec.startswith("openai:"):
        return OpenAICompatibleEvaluator(model_name=spec.split(":", 1)[1])
    if spec.startswith("openrouter:"):
        return OpenAICompatibleEvaluator(
            model_name=spec.split(":", 1)[1],
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    if spec.startswith("groq:"):
        return OpenAICompatibleEvaluator(
            model_name=spec.split(":", 1)[1],
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
    if spec.startswith("ollama:"):
        return OllamaVisionEvaluator(model_name=spec.split(":", 1)[1])
    raise ValueError(f"Unknown evaluator spec: {spec}")
