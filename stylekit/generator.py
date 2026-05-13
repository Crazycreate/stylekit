"""向后兼容外壳：原 StyleGenerator 直接代理到 OpenRouterProvider。

新代码请用 stylekit.providers.build_provider() / OpenRouterProvider / PollinationsProvider。
"""
from __future__ import annotations

from .providers import (
    DEFAULT_OPENROUTER_MODEL as DEFAULT_MODEL,
    GenerationResult,
    OpenRouterProvider,
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class StyleGenerator(OpenRouterProvider):
    """Legacy 名字，等同于 OpenRouterProvider。"""
    pass


__all__ = ["StyleGenerator", "GenerationResult", "DEFAULT_MODEL", "DEFAULT_BASE_URL"]
