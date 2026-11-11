"""Font generation.

Two sources, one goal: text that looks like it was shipped in 1994.

* ``patch_font`` builds a BMFont from the ``STCFN*`` graphics inside the
  WAD (the status-bar / menu font).  That is the authentic DOOM face and
  it is used for menus, headers and numbers.
* ``ttf_font`` rasterises a TTF at 1x with no anti-aliasing and turns it
  into a BMFont.  It exists because the stock DOOM font has no Cyrillic,
  and the game text is Russian.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageFont

from .wadfile import Wad

__all__ = [
    "Glyph",
    "pack_bmfont",
    "patch_font",
    "ttf_font",
    "CYRILLIC",
]

# Printable ASCII that the DOOM font provides.
ASCII = [c for c in range(32, 96)] + [c for c in range(97, 123)]

CYRILLIC = (
    list(range(0x0410, 0x0450))  # А-я
    + [0x0401, 0x0451, 0x2116]  # Ё ё №
    + [0x00AB, 0x00BB, 0x2013, 0x2014, 0x2026, 0x2018, 0x2019, 0x201C, 0x201D]
)


class Glyph:
    __slots__ = ("code", "mask", "xoffset", "yoffset", "xadvance")

    def __init__(self, code: int, mask: Image.Image, xoffset: int, yoffset: int, xadvance: int):
        self.code = code
        self.mask = mask
        self.xoffset = xoffset
        self.yoffset = yoffset
        self.xadvance = xadvance


def pack_bmfont(
    glyphs: list[Glyph],
    out_fnt: Path,
    out_png: Path,
    *,
    name: str,
    line_height: int,
    base: int,
    atlas_width: int = 1024,
    pad: int = 1,
) -> Path:
    """Shelf-pack glyphs into an atlas and write a BMFont ``.fnt`` file."""
    glyphs = [g for g in glyphs if g.mask.width > 0 and g.mask.height > 0]

    order = sorted(glyphs, key=lambda g: (-g.mask.height, -g.mask.width))
    x = pad
    y = pad
    shelf_h = 0
    placements: dict[int, tuple[int, int]] = {}
    for g in order:
        if x + g.mask.width + pad > atlas_width:
            x = pad
            y += shelf_h + pad
            shelf_h = 0
        placements[g.code] = (x, y)
        x += g.mask.width + pad
        shelf_h = max(shelf_h, g.mask.height)

    atlas_h = 1
    while atlas_h < y + shelf_h + pad:
        atlas_h *= 2
    atlas_h = min(atlas_h, 4096)

    atlas = Image.new("L", (atlas_width, atlas_h), 0)
    for g in glyphs:
        px, py = placements[g.code]
        atlas.paste(g.mask, (px, py))

    ## Ren'Py image fonts are coloured through `twomap`, which samples the
    ## **red** channel as coverage (see renpy/display/module.py: linmap).
    ## Storing the mask in the alpha channel only makes every glyph render as
    ## a solid rectangle, so the mask goes into both RGB and alpha: that keeps
    ## the recolour path *and* the direct-blit path (pure white text) correct.
    rgba = Image.merge("RGBA", (atlas, atlas, atlas, atlas))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out_png, format="PNG", optimize=True)

    ## Ren'Py resolves the page file relative to the game directory, so keep
    ## the "fonts/" prefix that the .fnt itself lives under.
    page_ref = out_png.name
    parent = out_png.parent.name
    if parent and parent != "game" and out_png.parent.parent.name == "game":
        page_ref = f"{parent}/{out_png.name}"

    lines = [
        f'info face="{name}" size={line_height} bold=0 italic=0 charset="" unicode=1 '
        f"stretchH=100 smooth=0 aa=1 padding=0,0,0,0 spacing=1,1 outline=0",
        f"common lineHeight={line_height} base={base} scaleW={atlas_width} scaleH={atlas_h} "
        f"pages=1 packed=0",
        f'page id=0 file="{page_ref}"',
        f"chars count={len(glyphs)}",
    ]
    for g in sorted(glyphs, key=lambda g: g.code):
        px, py = placements[g.code]
        lines.append(
            f"char id={g.code} x={px} y={py} width={g.mask.width} height={g.mask.height} "
            f"xoffset={g.xoffset} yoffset={g.yoffset} xadvance={g.xadvance} page=0 chnl=15"
        )
    out_fnt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_fnt


# ------------------------------------------------------------------ DOOM font


def patch_font(
    wad: Wad,
    out_fnt: Path,
    out_png: Path,
    *,
    scale: int = 1,
    name: str = "doom",
    codes: list[int] | None = None,
) -> Path:
    """Build a BMFont from the WAD ``STCFN`` glyph patches."""
    codes = codes if codes is not None else [c for c in range(33, 96)]
    glyphs: list[Glyph] = []
    max_top = 0
    max_bottom = 0

    for code in codes:
        lump = f"STCFN{code:03d}"
        if lump not in wad:
            continue
        w, h, left, top, rows = wad.raw_patch(lump)
        mask = Image.new("L", (w * scale, h * scale), 0)
        mpx = mask.load()
        for cx in range(w):
            for cy in range(h):
                if rows[cx][cy] is None:
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        mpx[cx * scale + sx, cy * scale + sy] = 255
        glyphs.append(Glyph(code, mask, left * scale, top * scale, (left + w) * scale))
        max_top = max(max_top, top * scale)
        max_bottom = max(max_bottom, (top + h) * scale)

    # The DOOM font has no space: invent one, four cells wide.
    glyphs.append(Glyph(32, Image.new("L", (1, 1), 0), 0, 0, 4 * scale))

    line_height = max_bottom + max(1, scale)
    base = max_bottom
    return pack_bmfont(glyphs, out_fnt, out_png, name=name, line_height=line_height, base=base)


def read_metrics(fnt: Path) -> dict[str, int]:
    """Pull lineHeight/base/scale out of a BMFont text file."""
    metrics = {"line_height": 0, "base": 0}
    for line in fnt.read_text(encoding="utf-8").splitlines():
        if line.startswith("common "):
            for part in line.split()[1:]:
                key, _, value = part.partition("=")
                if key == "lineHeight":
                    metrics["line_height"] = int(value)
                elif key == "base":
                    metrics["base"] = int(value)
    return metrics


# ------------------------------------------------------------------- TTF font


def ttf_font(
    ttf: Path,
    out_fnt: Path,
    out_png: Path,
    *,
    size: int,
    name: str = "cyr",
    codes: list[int] | None = None,
    threshold: int = 100,
    tracking: int = 0,
) -> Path:
    """Rasterise a TTF without anti-aliasing and pack it as a BMFont."""
    font = ImageFont.truetype(str(ttf), size)
    ascent, descent = font.getmetrics()
    base = ascent
    line_height = ascent + descent + max(1, size // 12)

    if codes is None:
        codes = ASCII + CYRILLIC

    glyphs: list[Glyph] = []
    for code in codes:
        ch = chr(code)
        try:
            advance = int(round(font.getlength(ch)))
        except Exception:
            advance = size // 2
        mask_img = font.getmask(ch)
        if mask_img.size[0] == 0 or mask_img.size[1] == 0:
            glyphs.append(Glyph(code, Image.new("L", (1, 1), 0), 0, 0, max(1, advance + tracking)))
            continue
        gray = Image.frombytes("L", mask_img.size, bytes(mask_img))
        bilevel = gray.point(lambda v: 255 if v >= threshold else 0)
        bbox = bilevel.getbbox()
        if bbox is None:
            glyphs.append(Glyph(code, Image.new("L", (1, 1), 0), 0, 0, max(1, advance + tracking)))
            continue
        cropped = bilevel.crop(bbox)
        xoffset = bbox[0]
        yoffset = base - bbox[3]
        glyphs.append(Glyph(code, cropped, xoffset, yoffset, max(1, advance + tracking)))

    return pack_bmfont(glyphs, out_fnt, out_png, name=name, line_height=line_height, base=base)


def measure_advance(ttf: Path, size: int, text: str) -> int:
    font = ImageFont.truetype(str(ttf), size)
    return int(math.ceil(font.getlength(text)))