"""
VLClient: OpenAI-compatible client for Qwen2.5-VL-7B-AWQ served by vLLM.

Start the server with:  bash scripts/start_vllm_vl.sh
Default endpoint:       http://localhost:8001/v1
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Optional

from openai import OpenAI

# ── Prompt templates ──────────────────────────────────────────────────────────

_INSPECT_PROMPT = """\
Answer the following question about this image: {question}

After your answer, output exactly one raw JSON object (no code fences) on its own line:
{{"entities_found": ["entity1", "entity2"], "relations_found": [{{"subject": "...", "relation": "...", "object": "..."}}]}}"""

_ENTITIES_PROMPT = """\
List all distinct objects, people, and scenes visible in this image.
Output exactly one raw JSON object (no code fences):
{{"entities": [{{"name": "...", "type": "person|object|scene", "attributes": {{"key": "value"}}}}]}}"""


class VLClient:
    """
    Thin wrapper around the vLLM OpenAI-compatible API for Qwen2.5-VL.

    All image inputs are passed as base64-encoded data URIs so no HTTP
    image hosting is needed.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001/v1",
        api_key: str = "token-abc",
        model: str = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _encode(image_path: str) -> tuple[str, str]:
        """Return (base64_data, mime_type) for a local image file."""
        suffix = Path(image_path).suffix.lstrip(".").lower()
        mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode(), mime

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

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """Find the first {...} JSON block in arbitrary VLM output."""
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}', text, re.DOTALL)
        if not match:
            # fallback: broader search
            match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    # ── public API ────────────────────────────────────────────────────────────

    def caption_frame(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail, including all people, objects, actions, and spatial relationships.",
    ) -> str:
        """Return a free-form text description of the frame."""
        return self._call(image_path, prompt)

    def extract_entities(self, image_path: str) -> list[dict]:
        """
        Extract all entities visible in the frame.

        Returns
        -------
        list of {"name": str, "type": "person|object|scene", "attributes": dict}
        Falls back to [] if VLM output cannot be parsed as JSON.
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
        Answer a specific question about a frame and extract structured entities/relations.

        Returns
        -------
        {
            "answer": str,
            "entities_found": list[str],
            "relations_found": list[{"subject": str, "relation": str, "object": str}]
        }
        Structured fields fall back to [] if the VLM output cannot be parsed.
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
            # Answer = everything before the JSON block
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
