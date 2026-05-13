"""Basic usage: single style transformation."""
import os
from pathlib import Path

from dotenv import load_dotenv

from stylekit import StyleGenerator, find_preset

load_dotenv()
api_key = os.environ["OPENROUTER_API_KEY"]

photo = Path("me.jpg")  # your photo
output = Path("side_part.png")

style = find_preset("hairstyle:side_part")
gen = StyleGenerator(api_key)
result = gen.transform(photo, style, output)
print(f"Saved: {result.output_path}")
print(f"Cost: ${result.cost_usd:.4f}")
print(f"Time: {result.elapsed_s}s")
