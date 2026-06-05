"""
VLClient: OpenAI-compatible client for vision-language models.

Supports two backends (selected via configs/default.yaml or BACKEND env var):
  - "dashscope" → Alibaba DashScope (qwen-vl-plus/max-latest)
  - "vllm"      → Local vLLM server (Qwen2.5-VL-7B-AWQ)

Both backends use the same OpenAI SDK — only the base_url / api_key differ.

Factory functions:
    get_vl_client()   → VLClient  (vision model)
    get_llm_client()  → ChatOpenAI (text/agent model)
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

# ── Prompt templates ──────────────────────────────────────────────────────────

_INSPECT_PROMPT = """\
Answer the following question about this image: {question}

After answering, on a new line output strict JSON (no code block):
{{"entities_found": ["entity1", "entity2"], "relations_found": [{{"subject": "...", "relation": "...", "object": "..."}}]}}"""

_ENTITIES_PROMPT = """\
List all visible people, objects, and scenes in the image.
Output strict JSON (no code block):
{{"entities": [{{"name": "...", "type": "person|object|scene", "attributes": {{"key": "value"}}}}]}}"""


class VLClient:
    """
    Thin wrapper around the OpenAI-compatible API for Qwen VL models.

    All image inputs are base64-encoded data URIs — no HTTP image hosting needed.
    Images are auto-resized to image_max_size before encoding to control token cost.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        backend: Optional[str] = None,
        image_max_size: Optional[int] = None,
    ) -> None:
        from src.config import get_settings
        cfg = get_settings()
        ep = cfg.active_vl if backend is None else (
            cfg.models.vl if backend == "dashscope" else
            cfg.vllm.vl
        )
        resolved_key = (
            api_key
            or (cfg.dashscope_api_key if (backend or cfg.backend) == "dashscope"
                else cfg.vllm_api_key)
        )

        self.model = model or (
            ep.model_name if hasattr(ep, "model_name") else ep.model_name
        )
        self.max_tokens = max_tokens or cfg.models.vl.max_tokens
        self.temperature = temperature if temperature is not None else cfg.models.vl.temperature
        self._image_max_size = image_max_size or cfg.perception.image_max_size
        self._client = OpenAI(
            base_url=base_url or ep.base_url,
            api_key=resolved_key or "token-abc",
        )

    # ── image encoding ────────────────────────────────────────────────────────

    def _encode(self, image_path: str) -> tuple[str, str]:
        """Return (base64_data, mime_type) resizing to image_max_size."""
        from PIL import Image

        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > self._image_max_size:
            scale = self._image_max_size / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode(), "jpeg"

    # ── JSON extraction ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """Find the first {...} JSON block in arbitrary VLM output."""
        # Try direct parse first (json_object mode returns clean JSON)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        # Extract first { ... last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None

    # ── single-image call ─────────────────────────────────────────────────────

    def _call(self, image_path: str, text_prompt: str) -> str:
        b64, mime = self._encode(image_path)
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{mime};base64,{b64}"},
                    },
                    {"type": "text", "text": text_prompt},
                ],
            }],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    # ── multi-image call ──────────────────────────────────────────────────────

    def call_multi(
        self,
        image_paths: list[str],
        text_prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
    ) -> str:
        """
        Call the VLM with multiple images in a single request.

        Args:
            image_paths:   Ordered list of local JPEG/PNG paths.
            text_prompt:   User-turn text (prompt placed after all images).
            system_prompt: Optional system instruction.
            json_mode:     When True, request response_format=json_object (used by
                           scene-graph building). Set False for free-form / short
                           plain-text answers (e.g. the QA baseline), otherwise the
                           model is forced to wrap its answer in a JSON object.

        Returns:
            Raw response string (JSON string when JSON mode succeeds).
        """
        content: list[dict] = []
        for path in image_paths:
            b64, mime = self._encode(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{mime};base64,{b64}"},
            })
        content.append({"type": "text", "text": text_prompt})

        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        kwargs: dict = dict(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        if not json_mode:
            return (self._client.chat.completions.create(**kwargs)
                    .choices[0].message.content or "")

        # Try JSON object mode; fall back silently if the model doesn't support it
        try:
            resp = self._client.chat.completions.create(
                **kwargs,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.debug("json_object mode failed (%s), retrying without", exc)
            resp = self._client.chat.completions.create(**kwargs)

        return resp.choices[0].message.content or ""

    # ── public API ────────────────────────────────────────────────────────────

    def caption_frame(
        self,
        image_path: str,
        prompt: str = "Describe in detail all the people, objects, actions, and "
                      "spatial relations in this image.",
    ) -> str:
        """Return a free-form text description of the frame."""
        return self._call(image_path, prompt)

    def extract_entities(self, image_path: str) -> list[dict]:
        """
        Extract all entities visible in the frame.

        Returns
        -------
        list of {"name": str, "type": str, "attributes": dict}
        Falls back to [] if VLM output cannot be parsed.
        """
        raw = self._call(image_path, _ENTITIES_PROMPT)
        parsed = self._extract_json(raw)
        if parsed and "entities" in parsed:
            return [
                {
                    "name": str(e.get("name", "")),
                    "type": str(e.get("type", "object")),
                    "attributes": dict(e.get("attributes", {})),
                }
                for e in parsed["entities"]
                if e.get("name")
            ]
        return []

    def inspect(self, image_path: str, question: str) -> dict:
        """
        Answer a specific question and extract structured entities / relations.

        Returns
        -------
        {
            "answer": str,
            "entities_found": list[str],
            "relations_found": list[{"subject", "relation", "object"}]
        }
        """
        prompt = _INSPECT_PROMPT.format(question=question)
        raw = self._call(image_path, prompt)

        parsed = self._extract_json(raw)
        if parsed:
            entities = [str(e) for e in parsed.get("entities_found", [])]
            relations = [
                r for r in parsed.get("relations_found", [])
                if isinstance(r, dict)
                and all(k in r for k in ("subject", "relation", "object"))
            ]
            try:
                json_start = raw.index("{")
                answer = raw[:json_start].strip()
            except ValueError:
                answer = raw.strip()

            return {
                "answer":          answer or raw.strip(),
                "entities_found":  entities,
                "relations_found": relations,
            }

        return {
            "answer":          raw.strip(),
            "entities_found":  [],
            "relations_found": [],
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def get_vl_client(backend: Optional[str] = None) -> VLClient:
    """Return a VLClient configured for the active backend."""
    return VLClient(backend=backend)


def get_llm_client(backend: Optional[str] = None):
    """
    Return a LangChain ChatOpenAI instance for the LLM endpoint.
    Used by the ReAct agent and other components that need text generation.
    """
    from langchain_openai import ChatOpenAI
    from src.config import get_settings

    cfg = get_settings()
    ep = cfg.active_llm if backend is None else (
        cfg.models.llm if (backend or cfg.backend) == "dashscope"
        else cfg.vllm.llm
    )
    api_key = (
        cfg.dashscope_api_key if (backend or cfg.backend) == "dashscope"
        else cfg.vllm_api_key
    )

    return ChatOpenAI(
        model=ep.model_name if hasattr(ep, "model_name") else ep.model_name,
        base_url=ep.base_url,
        api_key=api_key or "token-abc",
        temperature=cfg.models.llm.temperature,
        max_tokens=cfg.models.llm.max_tokens,
    )
