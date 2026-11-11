"""Render a sample line with a generated BMFont so a human can eyeball it."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SAMPLE_CYR = "Сержант, у нас проблема: демоны требуют профсоюз. Ёё №17"
SAMPLE_LAT = "RIP AND TEAR 0123456789 MAP31 BFG-9000"


def parse_fnt(fnt: Path) -> tuple[dict, dict[int, dict], Image.Image]:
    common: dict = {}
    chars: dict[int, dict] = {}
    page_file = None
    for line in fnt.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        kind = parts[0]
        args = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        if kind == "common":
            common = {k: int(v) for k, v in args.items() if k in ("lineHeight", "base", "scaleW", "scaleH")}
        elif kind == "page":
            page_file = args["file"].strip('"')
        elif kind == "char":
            chars[int(args["id"])] = {k: int(v) for k, v in args.items() if k != "id"}
    page = Image.open(fnt.parent / page_file).convert("RGBA")
    return common, chars, page


def render(fnt: Path, text: str, color=(240, 220, 190)) -> Image.Image:
    common, chars, page = parse_fnt(fnt)
    width = sum(chars.get(ord(c), {}).get("xadvance", 6) for c in text) + 20
    height = common["lineHeight"] + 8
    out = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(out)
    x = 4
    for c in text:
        info = chars.get(ord(c))
        if info is None:
            draw.rectangle([x, 4, x + 4, height - 4], outline=(255, 0, 0, 255))
            x += 6
            continue
        if info["width"] and info["height"]:
            glyph = page.crop(
                (
                    info["x"],
                    info["y"],
                    info["x"] + info["width"],
                    info["y"] + info["height"],
                )
            )
            alpha = glyph.getchannel("A")
            tinted = Image.new("RGBA", glyph.size, (*color, 0))
            tinted.putalpha(alpha)
            out.alpha_composite(tinted, (x + info["xoffset"], 4 + info["yoffset"]))
        x += info["xadvance"]
    return out


def main() -> None:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\DartPower\AppData\Local\Temp\opencode\dn_preview")
    fonts = Path(__file__).resolve().parents[1] / "game" / "fonts"
    tiles = []
    for name, text in (
        ("cyr20", SAMPLE_CYR),
        ("cyr26", SAMPLE_CYR),
        ("cyr32", SAMPLE_CYR),
        ("cyr44", "АД — ЭТО ГРАФИК"),
        ("doom1", SAMPLE_LAT),
        ("doom2", SAMPLE_LAT),
        ("doom3", "DOOM II"),
    ):
        fnt = fonts / f"{name}.fnt"
        if not fnt.exists():
            print("missing", fnt)
            continue
        tiles.append(render(fnt, text))
    total_h = sum(t.height + 6 for t in tiles)
    canvas = Image.new("RGBA", (max(t.width for t in tiles), total_h), (12, 10, 10, 255))
    y = 0
    for t in tiles:
        canvas.alpha_composite(t, (0, y))
        y += t.height + 6
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas.save(out_dir / "font_sample.png")
    print("wrote", out_dir / "font_sample.png")


if __name__ == "__main__":
    main()