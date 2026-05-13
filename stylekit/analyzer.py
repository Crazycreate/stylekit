"""Face analyzer — uses a vision LLM to determine face shape, skin tone, etc., for smart preset filtering."""
from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

DEFAULT_ANALYZE_MODEL = "anthropic/claude-sonnet-4.5"

ANALYZE_PROMPT = """Analyze this person's photo for the purpose of recommending hairstyles, hair colors, and outfits.
Respond ONLY with strict JSON (no markdown fences), using these exact fields:

{
  "gender": "male" | "female" | "unknown",
  "age_estimate": <int 16-65>,
  "face_shape": "oval" | "round" | "square" | "oblong" | "heart" | "diamond",
  "skin_tone": "warm" | "cool" | "neutral",
  "skin_tone_depth": "very_fair" | "fair" | "medium" | "tan" | "deep",
  "current_hair_length": "very_short" | "short" | "medium" | "long",
  "current_hair_color": "natural_black" | "dark_brown" | "brown" | "blonde" | "dyed_other",
  "wears_glasses": true | false,
  "forehead": "high" | "medium" | "low",
  "jawline": "sharp" | "soft" | "round",
  "vibe": "<one short Chinese phrase describing overall vibe, e.g. '温柔知性' / '阳光帅气'>",
  "suggested_directions": [
    "<one sentence in Chinese, what to improve>",
    "<one sentence in Chinese, what to avoid>"
  ]
}"""


@dataclass
class FaceAnalysis:
    gender: str
    age_estimate: int
    face_shape: str
    skin_tone: str
    skin_tone_depth: str
    current_hair_length: str
    current_hair_color: str
    wears_glasses: bool
    forehead: str
    jawline: str
    vibe: str
    suggested_directions: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class FaceAnalyzer:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_ANALYZE_MODEL,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def analyze(self, image: Path) -> FaceAnalysis:
        image = Path(image)
        mime = "image/jpeg" if image.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        b64 = base64.b64encode(image.read_bytes()).decode()
        dataurl = f"data:{mime};base64,{b64}"

        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ANALYZE_PROMPT},
                        {"type": "image_url", "image_url": {"url": dataurl}},
                    ],
                }],
                "temperature": 0.1,
                "max_tokens": 800,
            },
            timeout=120.0,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Analyze API HTTP {resp.status_code}: {resp.text[:300]}")
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
        return FaceAnalysis(**data)
