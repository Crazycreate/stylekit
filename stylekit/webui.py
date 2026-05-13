"""Gradio Web UI for stylekit.

Run with:
    pip install "stylekit[web]"
    stylekit web

Or programmatically:
    from stylekit.webui import build_app
    build_app().launch()
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .analyzer import FaceAnalyzer
from .config import get_api_key, get_setting
from .presets import Style, list_categories, load_presets
from .providers import (
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_POLLINATIONS_MODEL,
    build_provider,
)


CATEGORY_LABELS_ZH = {
    "hairstyle": "发型",
    "haircolor": "发色",
    "outfit": "穿搭",
    "accessory": "配饰",
    "makeup": "妆容",
    "multiview": "多视角",
}


def _category_choices() -> list[tuple[str, str]]:
    """Return [(label, value)] pairs so the dropdown shows '英文 (中文)' but yields the raw key."""
    return [
        (f"{c} ({CATEGORY_LABELS_ZH.get(c, c)})", c)
        for c in list_categories()
    ]


def _presets_for(category: str) -> list[Style]:
    return load_presets(category)


def _label(s: Style) -> str:
    return f"{s.slug}  —  {s.name_zh}"


def _resolve(style_label: str, category: str) -> Style:
    slug = style_label.split("  —  ", 1)[0].strip()
    for p in _presets_for(category):
        if p.slug == slug:
            return p
    raise ValueError(f"Unknown preset: {style_label}")


def build_app():
    """Construct and return the Gradio Blocks app (does not launch)."""
    try:
        import gradio as gr
    except ImportError as e:
        raise SystemExit(
            "Gradio is not installed. Install the web extra:\n"
            "    pip install 'stylekit[web]'\n"
            "or:\n"
            "    pip install gradio>=4.44"
        ) from e

    categories = list_categories()
    category_choices = _category_choices()
    default_cat = "hairstyle" if "hairstyle" in categories else categories[0]

    def on_category_change(cat: str):
        choices = [_label(s) for s in _presets_for(cat)]
        return gr.update(choices=choices, value=choices[0] if choices else None)

    def on_generate(
        photo_path: str | None,
        category: str,
        style_label: str,
        provider_name: str,
        model_name: str,
    ):
        if not photo_path:
            raise gr.Error("请先上传一张正面照")
        if not style_label:
            raise gr.Error("请选择一个预设")

        style = _resolve(style_label, category)

        if provider_name == "openrouter":
            key = get_api_key()
            if not key:
                raise gr.Error(
                    "未配置 OpenRouter API key。请先在终端运行 `stylekit setup`，"
                    "或切换到 pollinations 免费模式。"
                )
            provider = build_provider(
                "openrouter",
                api_key=key,
                model=model_name or DEFAULT_OPENROUTER_MODEL,
            )
        else:
            provider = build_provider(
                "pollinations",
                model=model_name or DEFAULT_POLLINATIONS_MODEL,
            )

        out_dir = Path(tempfile.mkdtemp(prefix="stylekit_web_"))
        out = out_dir / f"{style.category}_{style.id}.png"
        result = provider.transform(Path(photo_path), style, out)

        cost = f"${result.cost_usd:.4f}" if result.cost_usd > 0 else "免费"
        meta = (
            f"**{style.name_zh}** (`{style.slug}`)\n\n"
            f"- provider: `{result.provider}` · model: `{result.model}`\n"
            f"- 耗时: {result.elapsed_s}s · 尝试次数: {result.attempts}\n"
            f"- 花费: {cost}\n"
            f"- 输出: `{result.output_path}`"
        )
        return str(result.output_path), meta

    def on_analyze(photo_path: str | None):
        if not photo_path:
            raise gr.Error("请先上传一张正面照")
        key = get_api_key()
        if not key:
            raise gr.Error("人像分析需要 OpenRouter key，先运行 `stylekit setup`")
        face = FaceAnalyzer(key).analyze(Path(photo_path))
        d = face.to_dict()
        lines = [
            f"**脸型** {d['face_shape']}  |  **肤色** {d['skin_tone']}/{d['skin_tone_depth']}",
            f"**性别** {d['gender']}  |  **年龄** ~{d['age_estimate']}",
            f"**气质** {d['vibe']}",
            "",
            "**改造建议**：",
        ] + [f"- {s}" for s in d["suggested_directions"]]
        return "\n".join(lines)

    default_provider = get_setting("default_provider") or (
        "openrouter" if get_api_key() else "pollinations"
    )

    with gr.Blocks(title="stylekit — AI 试发型 / 试穿搭") as demo:
        gr.Markdown(
            "# 🎨 stylekit\n"
            "AI 试发型 / 试发色 / 试穿搭 / 试配饰 / 试妆容 / 多视角。\n"
            "_走进理发店之前，先看看效果。_"
        )

        with gr.Row():
            with gr.Column(scale=1):
                photo = gr.Image(label="正面照", type="filepath", height=380)
                analyze_btn = gr.Button("🔍 AI 分析人像", variant="secondary")
                analysis_md = gr.Markdown()

            with gr.Column(scale=1):
                category = gr.Dropdown(
                    choices=category_choices,
                    value=default_cat,
                    label="类别 / Category",
                )
                preset = gr.Dropdown(
                    choices=[_label(s) for s in _presets_for(default_cat)],
                    label="预设",
                    value=(
                        _label(_presets_for(default_cat)[0])
                        if _presets_for(default_cat)
                        else None
                    ),
                )
                provider = gr.Radio(
                    choices=["openrouter", "pollinations"],
                    value=default_provider,
                    label="Provider",
                    info="openrouter=付费高质量保脸 · pollinations=免费但不保脸",
                )
                model = gr.Textbox(
                    label="模型（留空用默认）",
                    placeholder=f"{DEFAULT_OPENROUTER_MODEL}  /  {DEFAULT_POLLINATIONS_MODEL}",
                )
                generate_btn = gr.Button("✨ 生成", variant="primary")

            with gr.Column(scale=1):
                output_image = gr.Image(label="生成结果", height=380)
                meta_md = gr.Markdown()

        category.change(on_category_change, inputs=category, outputs=preset)
        analyze_btn.click(on_analyze, inputs=photo, outputs=analysis_md)
        generate_btn.click(
            on_generate,
            inputs=[photo, category, preset, provider, model],
            outputs=[output_image, meta_md],
        )

    return demo


def launch(
    *,
    host: str = "127.0.0.1",
    port: int = 7860,
    share: bool = False,
) -> None:
    """Launch the Gradio app (blocking)."""
    import gradio as gr
    build_app().launch(
        server_name=host,
        server_port=port,
        share=share,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    launch()
