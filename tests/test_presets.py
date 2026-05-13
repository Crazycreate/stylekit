"""Smoke tests — no API calls, just structural validation."""
import pytest

from stylekit.presets import find_preset, list_categories, load_presets


def test_presets_load():
    presets = load_presets()
    assert len(presets) > 20, f"Expected 20+ presets, got {len(presets)}"


def test_categories():
    cats = list_categories()
    assert "hairstyle" in cats
    assert "haircolor" in cats
    assert "outfit" in cats


def test_unique_ids_per_category():
    for cat in list_categories():
        ids = [p.id for p in load_presets(cat)]
        assert len(ids) == len(set(ids)), f"Duplicate ids in category {cat}: {ids}"


def test_find_preset():
    p = find_preset("hairstyle:side_part")
    assert p.id == "side_part"
    assert p.category == "hairstyle"


def test_find_preset_missing():
    with pytest.raises(KeyError):
        find_preset("hairstyle:nonexistent")


def test_find_preset_bad_slug():
    with pytest.raises(ValueError):
        find_preset("no-colon-here")


def test_fits_no_constraints():
    p = find_preset("haircolor:chocolate_brown")
    assert p.fits(face_shape="round", skin_tone="warm")  # 仅有 skin_tones=warm,neutral,cool


def test_fits_with_mismatch():
    p = find_preset("hairstyle:side_part")
    # side_part 不限 skin_tone，但限 gender=male
    assert p.fits(gender="male")
    assert not p.fits(gender="female")


def test_prompt_not_empty():
    for p in load_presets():
        assert p.prompt.strip(), f"Empty prompt for {p.slug}"
        assert len(p.prompt) > 50, f"Prompt too short for {p.slug}: {p.prompt[:80]}"
