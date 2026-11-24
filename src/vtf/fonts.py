"""Cross-platform font loading helpers backed by Matplotlib bundled fonts."""

from __future__ import annotations

from functools import lru_cache

from matplotlib import font_manager
from PIL import ImageFont


@lru_cache(maxsize=32)
def get_font(
    size: int = 16,
    *,
    bold: bool = False,
    mono: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a crisp TrueType font that renders identically across OSes."""
    family = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    weight = "bold" if bold else "normal"
    try:
        prop = font_manager.FontProperties(family=family, weight=weight)
        font_path = font_manager.findfont(prop, fallback_to_default=True)
        return ImageFont.truetype(font_path, size=size)
    except Exception:
        return ImageFont.load_default()
