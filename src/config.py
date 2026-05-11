"""
Unified configuration for Video Agent.

Load order (later sources override earlier ones):
  1. configs/default.yaml    — base parameters
  2. .env file               — API keys and local overrides
  3. Environment variables   — highest priority (CI / Docker)

Nested override via env: LLM__MODEL_NAME=foo, MODELS__VL__TEMPERATURE=0.2
API keys: DASHSCOPE_API_KEY, VLLM_API_KEY

Usage:
    from src.config import get_settings
    cfg = get_settings()
    print(cfg.models.vl.model_name)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_FILE = _PROJECT_ROOT / "configs" / "default.yaml"


# ── Sub-models ────────────────────────────────────────────────────────────────

class ModelEndpoint(BaseModel):
    provider: str = "dashscope"
    model_name: str = "qwen-vl-plus-latest"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = 0.1
    max_tokens: int = 2048


class ModelsSection(BaseModel):
    vl: ModelEndpoint = ModelEndpoint()
    llm: ModelEndpoint = ModelEndpoint(model_name="qwen-plus-latest")


class VLLMEndpoint(BaseModel):
    base_url: str = "http://localhost:8001/v1"
    model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ"


class VLLMSection(BaseModel):
    vl: VLLMEndpoint = VLLMEndpoint()
    llm: VLLMEndpoint = VLLMEndpoint(
        base_url="http://localhost:8000/v1",
        model_name="Qwen/Qwen3-8B",
    )


class PerceptionConfig(BaseModel):
    keyframe_strategy: str = "uniform"
    keyframe_count: int = 8
    image_max_size: int = 1280
    image_quality: int = 85
    frame_tolerance_sec: float = 2.0
    batch_size: int = 4
    max_parallel_batches: int = 3


class SceneGraphConfig(BaseModel):
    merge_window_sec: float = 3.0
    dedup_threshold: float = 0.9
    default_relation_vocab_size: int = 50
    confidence_threshold: float = 0.75
    max_display_triplets: int = 50
    timestamp_tolerance: float = 0.5


class RetrievalConfig(BaseModel):
    top_k: int = 10
    min_score: float = 0.5
    fallback_entity_count: int = 4
    embedding_dim: int = 384
    embedding_model: str = "all-MiniLM-L6-v2"


class AgentConfig(BaseModel):
    max_iterations: int = 10
    verbose: bool = True
    return_intermediate_steps: bool = True
    use_mock: bool = False


class MockConfig(BaseModel):
    enabled: bool = False
    video_duration: float = 120.0


# ── Top-level Settings ────────────────────────────────────────────────────────

class Settings(BaseSettings):
    """
    Top-level settings object.  YAML → .env → env vars, in that priority order.
    """
    backend: Literal["dashscope", "vllm"] = "dashscope"

    # API keys (never in YAML; always from .env or environment)
    dashscope_api_key: str = ""
    vllm_api_key: str = "token-abc"

    # Sections
    models: ModelsSection = ModelsSection()
    vllm: VLLMSection = VLLMSection()
    perception: PerceptionConfig = PerceptionConfig()
    scene_graph: SceneGraphConfig = SceneGraphConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    agent: AgentConfig = AgentConfig()
    mock: MockConfig = MockConfig()

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Convenience helpers ───────────────────────────────────────────────────

    @property
    def active_vl(self) -> ModelEndpoint:
        """Return the active VL model endpoint based on backend."""
        if self.backend == "vllm":
            ep = self.vllm.vl
            return ModelEndpoint(
                provider="vllm",
                model_name=ep.model_name,
                base_url=ep.base_url,
                temperature=self.models.vl.temperature,
                max_tokens=self.models.vl.max_tokens,
            )
        return self.models.vl

    @property
    def active_llm(self) -> ModelEndpoint:
        """Return the active LLM endpoint based on backend."""
        if self.backend == "vllm":
            ep = self.vllm.llm
            return ModelEndpoint(
                provider="vllm",
                model_name=ep.model_name,
                base_url=ep.base_url,
                temperature=self.models.llm.temperature,
                max_tokens=self.models.llm.max_tokens,
            )
        return self.models.llm

    @property
    def active_api_key(self) -> str:
        return self.vllm_api_key if self.backend == "vllm" else self.dashscope_api_key


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_settings() -> Settings:
    data: dict = {}
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    return Settings(**data)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return _load_settings()
