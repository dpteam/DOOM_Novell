"""Tiny BMFont renderer used to draw offline previews and promo shots.

The game itself does not need this: Ren'Py renders the same .fnt files at
runtime.  This module exists so `tools/promo_shots.py` can put readable
Russian text onto a still image without pulling in a text shaping library.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image

__all__ = ["BMFont", "draw_text", "wrap_text", "fit_lines"]


@dataclass
class Glyph:
    x: int
    y: int
    width: int
    height: int
    xoffset: int
    yoffset: int
    xadvance: int


class BMFont:
    def __init__(self, fnt: Path):
        self.path = Path(fnt)
        self.glyphs: dict[int, Glyph] = {}
        self.line_height = 0
        self.base = 0
        page = None

        for line in self.path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if not parts:
                continue
            kind = parts[0]
            args = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
            if kind == "common":
                self.line_height = int(args["lineHeight"])
                self.base = int(args["base"])
            elif kind == "page":
                page = args["file"].strip('"')
            elif kind == "char":
                self.glyphs[int(args["id"])] = Glyph(
                    int(args["x"]),
                    int(args["y"]),
                    int(args["width"]),
                    int(args["height"]),
                    int(args["xoffset"]),
                    int(args["yoffset"]),
                    int(args["xadvance"]),
                )

        if page is None:
            raise ValueError(f"{fnt}: no page line")
        page_path = self.path.parent / page
        if not page_path.exists():
            # The .fnt may carry a "fonts/" prefix meant for Ren'Py.
            page_path = self.path.parent / Path(page).name
        self.page = Image.open(page_path).convert("RGBA")

    def advance(self, text: str) -> int:
        total = 0
        for char in text:
            glyph = self.glyphs.get(ord(char))
            total += glyph.xadvance if glyph else self.line_height // 2
        return total

    def text_height(self, lines: int = 1, spacing: int = 0) -> int:
        return lines * self.line_height + max(0, lines - 1) * spacing

    def draw(
        self,
        img: Image.Image,
        text: str,
        xy: tuple[int, int],
        color: tuple[int, int, int] = (246, 230, 207),
        *,
        shadow: tuple[int, int, int] | None = (0, 0, 0),
        alpha: int = 255,
        scale: int = 1,
    ) -> int:
        """Draw one line, returns the advance width."""
        x, y = xy
        start_x = x

        def stamp(x0: int, y0: int, col: tuple[int, int, int], a: int) -> None:
            tinted = Image.new("RGBA", (self.page.width, self.page.height), (*col, 0))
            tinted.putalpha(self.page.getchannel("A").point(lambda v: v * a // 255))
            img.alpha_composite(tinted, (x0, y0))

        for char in text:
            glyph = self.glyphs.get(ord(char))
            if glyph is None:
                x += self.line_height // 2
                continue
            if glyph.width and glyph.height:
                if shadow is not None:
                    region = self.page.crop(
                        (glyph.x, glyph.y, glyph.x + glyph.width, glyph.y + glyph.height)
                    )
                    sh = Image.new("RGBA", region.size, (*shadow, 0))
                    sh.putalpha(region.getchannel("A").point(lambda v: v * alpha // 255))
                    img.alpha_composite(
                        sh, (x + glyph.xoffset + 2, y + glyph.yoffset + 2)
                    )
                stamp(x + glyph.xoffset, y + glyph.yoffset, color, alpha)
            x += glyph.xadvance
        return x - start_x


def wrap_text(font: BMFont, text: str, max_width: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        trial = (current + " " + word).strip()
        if font.advance(trial) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_lines(font: BMFont, text: str, max_width: int, max_lines: int) -> list[str]:
    lines = wrap_text(font, text, max_width)
    if len(lines) <= max_lines:
        return lines
    kept = lines[: max_lines]
    kept[-1] = kept[-1].rstrip(" ,.") + "…"
    return kept


def draw_text(
    img: Image.Image,
    font: BMFont,
    text: str,
    xy: tuple[int, int],
    color: tuple[int, int, int] = (246, 230, 207),
    *,
    width: int | None = None,
    max_lines: int = 3,
    spacing: int = 4,
    shadow: tuple[int, int, int] | None = (0, 0, 0),
    alpha: int = 255,
) -> int:
    """Draw wrapped text; returns the bottom y of the last line."""
    lines = fit_lines(font, text, width, max_lines) if width else [text]
    x, y = xy
    for i, line in enumerate(lines):
        font.draw(img, line, (x, y + i * (font.line_height + spacing)), color, shadow=shadow, alpha=alpha)
    return y + len(lines) * font.line_height + (len(lines) - 1) * spacing


def load(fonts_dir: Path, name: str) -> BMFont:
    return BMFont(fonts_dir / f"{name}.fnt")