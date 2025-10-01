# 02_config.py
from __future__ import annotations
import os
from pydantic import BaseModel, Field

class Config(BaseModel):
    # VLM Provider selection
    vlm_provider: str = "openrouter"  # "openrouter", "local", "direct"

    # OpenRouter.ai configuration
    openrouter_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Unified model configuration (used for all VLM providers)
    model_name: str = "google/gemini-2.5-flash"
    vlm_endpoint: str = "http://localhost:12345/v1/vision/extract"  # uprav dle reálu
    use_vlm_stub: bool = False

    # PDF render
    dpi: int = 200
    max_pages: int = 2

    # Pairing
    id_min_digits: int = 4
    id_max_digits: int = 8

    # Tolerance
    tolerance_warn: int = 3
    tolerance_fail: int = 6

    # IO
    out_root: str = "_debug_outputs"
    log_file: str | None = None