"""stylekit — AI-powered try-on for hairstyles, hair colors, and outfits."""
from .generator import StyleGenerator, GenerationResult
from .analyzer import FaceAnalyzer, FaceAnalysis
from .presets import Style, load_presets, list_categories, find_preset
from .config import get_api_key, load_config, save_config, config_path

__version__ = "0.1.0"
__all__ = [
    "StyleGenerator",
    "GenerationResult",
    "FaceAnalyzer",
    "FaceAnalysis",
    "Style",
    "load_presets",
    "list_categories",
    "find_preset",
    "get_api_key",
    "load_config",
    "save_config",
    "config_path",
]
