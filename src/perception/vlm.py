"""
VLM wrapper for Qwen2.5-VL-7B-AWQ.

In mock mode, returns pre-defined responses without loading any model.
In real mode, calls the VLM via vLLM's OpenAI-compatible API.
"""

from __future__ import annotations

import os
from typing import Optional


class VLMPerception:
    """
    Singleton wrapper around Qwen2.5-VL-7B-AWQ.
    Access via VLMPerception.get_instance() to avoid duplicate model loads.
    """

    _instance: Optional["VLMPerception"] = None

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
        base_url: str = "http://localhost:8001/v1",
        api_key: str = "token-abc",
        use_mock: bool = True,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.use_mock = use_mock
        self._client = None

        if not use_mock:
            self._init_client()

    @classmethod
    def get_instance(cls, use_mock: bool = True) -> "VLMPerception":
        if cls._instance is None:
            cls._instance = cls(
                base_url=os.getenv("VLM_BASE_URL", "http://localhost:8001/v1"),
                api_key=os.getenv("VLM_API_KEY", "token-abc"),
                use_mock=use_mock,
            )
        return cls._instance

    def _init_client(self) -> None:
        # TODO: initialize OpenAI client pointing to vLLM VLM endpoint
        #
        # from openai import OpenAI
        # self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        raise NotImplementedError("Real VLM client not yet initialized.")

    # ── Public API ────────────────────────────────────────────────────────────

    def describe_frame(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail, focusing on people, objects, and their spatial relationships.",
    ) -> str:
        """Return a free-form text description of a single frame."""
        if self.use_mock:
            return (
                "A person in a red jacket rides a blue bicycle along a city street. "
                "A green traffic light is visible ahead. The road is empty."
            )
        # TODO: real inference via vLLM OpenAI endpoint
        #
        # import base64
        # with open(image_path, "rb") as f:
        #     b64 = base64.b64encode(f.read()).decode()
        # response = self._client.chat.completions.create(
        #     model=self.model_name,
        #     messages=[{
        #         "role": "user",
        #         "content": [
        #             {"type": "image_url",
        #              "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        #             {"type": "text", "text": prompt},
        #         ],
        #     }],
        #     max_tokens=512,
        # )
        # return response.choices[0].message.content
        raise NotImplementedError

    def extract_triplets(
        self,
        image_path: str,
        focus_entities: Optional[list[str]] = None,
        timestamp: float = 0.0,
    ) -> list[dict]:
        """
        Extract scene graph triplets from a single frame.

        Returns
        -------
        list of dicts with keys:
            subject, relation, object, t_start, t_end, confidence, source
        """
        if self.use_mock:
            return [
                {
                    "subject": "person_A", "relation": "riding",
                    "object": "bicycle",
                    "t_start": timestamp, "t_end": timestamp + 2.5,
                    "confidence": 0.92, "source": "vlm",
                },
                {
                    "subject": "bicycle", "relation": "on",
                    "object": "road",
                    "t_start": timestamp, "t_end": timestamp + 2.5,
                    "confidence": 0.87, "source": "vlm",
                },
            ]
        # TODO: structured output extraction via VLM
        # Prompt the VLM with a schema-guided prompt, parse JSON response.
        raise NotImplementedError

    def answer_question(self, image_path: str, question: str) -> str:
        """Answer a specific question about a frame (used by inspect_frame tool)."""
        if self.use_mock:
            return (
                f"[MOCK VLM] Answering '{question}': The frame shows a cyclist at "
                f"an intersection with a green traffic light."
            )
        # TODO: same call as describe_frame but with the user's question
        raise NotImplementedError
