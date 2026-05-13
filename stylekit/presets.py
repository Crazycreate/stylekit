"""Preset loader — read YAML files under stylekit/presets/."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PRESETS_DIR = Path(__file__).parent / "presets"


@dataclass
class Style:
    id: str
    name_zh: str
    name_en: str
    category: str  # 'hairstyle' | 'haircolor' | 'outfit'
    subcategory: str
    prompt: str
    description_zh: str = ""
    description_en: str = ""
    best_for: dict = field(default_factory=dict)
    source_file: str = ""

    @property
    def slug(self) -> str:
        return f"{self.category}:{self.id}"

    def fits(self, face_shape: str | None = None, skin_tone: str | None = None,
             gender: str | None = None) -> bool:
        """Loose match based on best_for tags. Empty best_for means 'fits everyone'."""
        bf = self.best_for or {}
        if face_shape and bf.get("face_shapes") and face_shape not in bf["face_shapes"]:
            return False
        if skin_tone and bf.get("skin_tones") and skin_tone not in bf["skin_tones"]:
            return False
        if gender and bf.get("gender") and gender != bf["gender"]:
            return False
        return True


def _load_yaml_file(path: Path) -> list[Style]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    out: list[Style] = []
    for item in raw:
        out.append(Style(
            id=item["id"],
            name_zh=item.get("name_zh", item["id"]),
            name_en=item.get("name_en", item["id"]),
            category=item["category"],
            subcategory=item.get("subcategory", "default"),
            prompt=item["prompt"].strip(),
            description_zh=item.get("description_zh", "").strip(),
            description_en=item.get("description_en", "").strip(),
            best_for=item.get("best_for", {}),
            source_file=path.name,
        ))
    return out


def load_presets(category: str | None = None) -> list[Style]:
    """Load all presets, optionally filter by category ('hairstyle' | 'haircolor' | 'outfit')."""
    all_styles: list[Style] = []
    for yml in sorted(PRESETS_DIR.glob("*.yaml")):
        all_styles.extend(_load_yaml_file(yml))
    if category:
        return [s for s in all_styles if s.category == category]
    return all_styles


def list_categories() -> list[str]:
    return sorted({s.category for s in load_presets()})


def find_preset(slug: str) -> Style:
    """Find a preset by slug (e.g. 'hairstyle:side_part'). Raises KeyError if not found."""
    if ":" not in slug:
        raise ValueError(f"Slug must be 'category:id', got: {slug}")
    category, sid = slug.split(":", 1)
    for s in load_presets(category):
        if s.id == sid:
            return s
    raise KeyError(f"No preset found for {slug}")
