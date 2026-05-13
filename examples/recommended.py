"""Smart recommendation: analyze face first, then generate top-N fitting variants."""
import os
from pathlib import Path

from dotenv import load_dotenv

from stylekit import FaceAnalyzer, StyleGenerator, load_presets
from stylekit.grid import build_grid

load_dotenv()
api_key = os.environ["OPENROUTER_API_KEY"]

photo = Path("me.jpg")
out_dir = Path("recommended")
out_dir.mkdir(exist_ok=True)

# 1) 分析
analyzer = FaceAnalyzer(api_key)
face = analyzer.analyze(photo)
print(f"Face: {face.face_shape}, Skin: {face.skin_tone}, Gender: {face.gender}")
print(f"Vibe: {face.vibe}")
for s in face.suggested_directions:
    print(f"  - {s}")

# 2) 按合适度筛选发型
candidates = [
    p for p in load_presets("hairstyle")
    if p.fits(face_shape=face.face_shape, skin_tone=face.skin_tone, gender=face.gender)
]
picks = candidates[:6]

# 3) 批量生成
gen = StyleGenerator(api_key)
results = []
for p in picks:
    print(f"Generating {p.slug}...")
    r = gen.transform(photo, p, out_dir / f"{p.id}.png")
    results.append(r)
    print(f"  -> {r.elapsed_s}s, ${r.cost_usd:.4f}")

# 4) 拼对比图
build_grid(
    [r.output_path for r in results],
    labels=[p.name_zh for p in picks],
    output=out_dir / "_grid.jpg",
    source=photo,
)
print(f"\nGrid saved at {out_dir / '_grid.jpg'}")
