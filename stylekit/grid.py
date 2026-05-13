"""Build a comparison grid image — useful for sharing all variants in one shot."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def build_grid(
    images: list[Path],
    labels: list[str] | None = None,
    output: Path = Path("grid.jpg"),
    source: Path | None = None,
    thumb_size: int = 512,
    cols: int | None = None,
    bg_color: tuple = (24, 24, 24),
    text_color: tuple = (240, 240, 240),
    padding: int = 16,
    label_height: int = 56,
) -> Path:
    """Compose a labeled grid. If `source` is given, it goes first as "原图"."""
    if source:
        images = [Path(source)] + list(images)
        labels = ["原图"] + (labels or [Path(p).stem for p in images[1:]])
    if not labels:
        labels = [Path(p).stem for p in images]

    n = len(images)
    cols = cols or min(4, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)

    cell_w = thumb_size
    cell_h = thumb_size + label_height
    grid_w = cols * cell_w + (cols + 1) * padding
    grid_h = rows * cell_h + (rows + 1) * padding

    grid = Image.new("RGB", (grid_w, grid_h), bg_color)
    draw = ImageDraw.Draw(grid)

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    except OSError:
        font = ImageFont.load_default()

    for idx, (img_path, label) in enumerate(zip(images, labels)):
        r, c = divmod(idx, cols)
        x = padding + c * (cell_w + padding)
        y = padding + r * (cell_h + padding)

        im = Image.open(img_path).convert("RGB")
        im.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
        off_x = (thumb_size - im.width) // 2
        off_y = (thumb_size - im.height) // 2
        grid.paste(im, (x + off_x, y + off_y))

        # 标签
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(label, font=font)
        text_x = x + (cell_w - tw) // 2
        text_y = y + thumb_size + 10
        draw.text((text_x, text_y), label, fill=text_color, font=font)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    grid.save(output, "JPEG", quality=90)
    return output
