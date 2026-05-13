"""图像生成 provider 抽象。

支持：
  - OpenRouterProvider (默认，付费，质量最好)
  - PollinationsProvider (免费，无需 key，质量较弱)

接入新 provider：继承 Provider 并实现 transform()。
"""
from __future__ import annotations

import base64
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from .presets import Style

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
POLLINATIONS_BASE = "https://image.pollinations.ai"

PRESERVE_INSTRUCT = """Keep absolutely identical: the subject's face (all features, skin tone, eye shape, lip shape), age, any eyewear, expression, clothing (unless this is an outfit change), background, lighting, camera angle, and pose. Output a photorealistic portrait of the same person with only the specified change applied."""


@dataclass
class GenerationResult:
    style_slug: str
    output_path: Path
    cost_usd: float = 0.0
    elapsed_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    attempts: int = 1
    provider: str = ""
    model: str = ""


class Provider(ABC):
    name: str = "base"
    requires_key: bool = True
    is_free: bool = False

    @abstractmethod
    def transform(self, source_image: Path, style: Style, output_path: Path,
                  extra: str = "") -> GenerationResult: ...

    @staticmethod
    def _change_clause(category: str) -> str:
        return {
            "hairstyle": "change ONLY the hairstyle (cut, shape, length, texture)",
            "haircolor": "change ONLY the hair color, keep the exact same cut/shape/length",
            "outfit": "change ONLY the clothing, keep hair and face identical",
            "accessory": "add the specified accessory naturally; do NOT alter face, hair, or clothing otherwise",
            "makeup": "apply ONLY the specified makeup look; keep hair, clothing, face structure and skin texture identical (no skin smoothing, no face reshaping)",
            "multiview": "regenerate the SAME PERSON from the specified camera angle / framing; keep face identity, hair, makeup, clothing, and lighting identical",
        }.get(category, f"change the {category}")

    @staticmethod
    def _detect_mime(path: Path) -> str:
        ext = path.suffix.lower()
        return {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
        }.get(ext, "image/jpeg")


# ─────────────────────────────────── OpenRouter ───────────────────────────────────

DEFAULT_OPENROUTER_MODEL = "openai/gpt-5.4-image-2"


class OpenRouterProvider(Provider):
    name = "openrouter"
    requires_key = True
    is_free = False

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_OPENROUTER_MODEL,
        base_url: str = OPENROUTER_BASE,
        timeout: float = 600.0,
        max_retries: int = 3,
        retry_backoff_s: float = 10.0,
    ):
        if not api_key:
            raise ValueError("OpenRouter API key is required")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s

    def transform(self, source_image, style, output_path, extra=""):
        source_image = Path(source_image)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        b64 = base64.b64encode(source_image.read_bytes()).decode()
        dataurl = f"data:{self._detect_mime(source_image)};base64,{b64}"
        prompt = (
            f"Edit this photo: {self._change_clause(style.category)}\n\n"
            f"{PRESERVE_INSTRUCT}\n\n{extra.strip()}\n\n"
            f"NEW {style.category.upper()}:\n{style.prompt}"
        )

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            t0 = time.time()
            try:
                resp = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": dataurl}},
                            ],
                        }],
                        "modalities": ["image", "text"],
                    },
                    timeout=self.timeout,
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                msg = data["choices"][0]["message"]
                images = msg.get("images") or []
                if not images:
                    raise RuntimeError("API returned no image")
                img = images[0]
                url = img.get("image_url", {}).get("url") if isinstance(img, dict) else img
                if url and url.startswith("data:image"):
                    output_path.write_bytes(base64.b64decode(url.split(",", 1)[1]))
                elif url and url.startswith("http"):
                    output_path.write_bytes(httpx.get(url, timeout=120).content)
                else:
                    raise RuntimeError(f"Unknown image url: {str(img)[:200]}")
                usage = data.get("usage", {})
                return GenerationResult(
                    style_slug=style.slug, output_path=output_path,
                    cost_usd=float(usage.get("cost", 0)),
                    elapsed_s=round(time.time() - t0, 1),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    attempts=attempt, provider=self.name, model=self.model,
                )
            except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectTimeout,
                    httpx.NetworkError, RuntimeError) as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_s)
                continue
            except Exception as e:
                last_err = e
                break
        raise RuntimeError(f"Failed after {self.max_retries} attempts: {last_err}")


# ─────────────────────────────────── Pollinations (free) ───────────────────────────────────

DEFAULT_POLLINATIONS_MODEL = "flux"  # 也支持: turbo, kontext


class PollinationsProvider(Provider):
    """免费、无需 key、零门槛。

    限制：
    - 主要是文生图，输入图作为风格/构图参考，**面部保留较弱**
    - 速率限制：单 IP 约 1 张/秒
    - 质量低于 OpenRouter 付费模型
    - 第三方服务，可能临时不可用
    """
    name = "pollinations"
    requires_key = False
    is_free = True

    def __init__(self, model: str = DEFAULT_POLLINATIONS_MODEL, timeout: float = 180.0,
                 max_retries: int = 3, retry_backoff_s: float = 5.0):
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s

    def transform(self, source_image, style, output_path, extra=""):
        source_image = Path(source_image)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Pollinations 不接受 image upload，只能依靠 prompt 完整描述目标人物
        prompt = (
            f"Photorealistic portrait of an Asian person, professional photo, "
            f"front-facing pose, neutral expression, studio lighting. "
            f"{style.prompt} "
            f"High detail face, sharp focus, natural skin texture."
        )

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            t0 = time.time()
            try:
                # GET 风格的 endpoint，参数全 URL 化
                url = (
                    f"{POLLINATIONS_BASE}/prompt/{quote(prompt)}"
                    f"?model={self.model}&width=1024&height=1024&nologo=true&private=true"
                )
                resp = httpx.get(url, timeout=self.timeout, follow_redirects=True)
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                ct = resp.headers.get("content-type", "")
                if not ct.startswith("image/"):
                    raise RuntimeError(f"Unexpected content-type: {ct}")
                output_path.write_bytes(resp.content)
                return GenerationResult(
                    style_slug=style.slug, output_path=output_path,
                    cost_usd=0.0, elapsed_s=round(time.time() - t0, 1),
                    attempts=attempt, provider=self.name, model=self.model,
                )
            except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectTimeout,
                    httpx.NetworkError, RuntimeError) as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_s)
                continue
            except Exception as e:
                last_err = e
                break
        raise RuntimeError(f"Pollinations failed after {self.max_retries} attempts: {last_err}")


# ─────────────────────────────────── 工厂 ───────────────────────────────────

def build_provider(name: str, api_key: str | None = None, model: str | None = None,
                   **kwargs) -> Provider:
    name = (name or "").lower()
    if name in ("openrouter", "or", ""):
        if not api_key:
            raise ValueError("OpenRouter 需要 API key，运行 `stylekit setup` 或用 --provider pollinations")
        return OpenRouterProvider(api_key=api_key, model=model or DEFAULT_OPENROUTER_MODEL, **kwargs)
    if name in ("pollinations", "poll", "free"):
        return PollinationsProvider(model=model or DEFAULT_POLLINATIONS_MODEL, **kwargs)
    raise ValueError(f"Unknown provider: {name}. 支持: openrouter, pollinations")
