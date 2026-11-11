"""Level geometry: parse MAPxx lumps and draw floor-plan "tactical maps".

These maps double as chapter cards and as content for the in-game level
archive, so they use the real sector shapes, floor flats and monster
placements instead of anything hand-drawn.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFilter

from .wadfile import Wad, average_color

__all__ = ["Level", "render_floorplan"]


@dataclass
class Sector:
    floor_height: int
    ceil_height: int
    floor_pic: str
    ceil_pic: str
    light: int
    special: int
    tag: int


@dataclass
class LineDef:
    v1: int
    v2: int
    flags: int
    special: int
    tag: int
    sides: tuple[int, int]


@dataclass
class Level:
    name: str
    vertices: list[tuple[int, int]]
    sectors: list[Sector]
    sidedefs: list[tuple[int, int, str, str, str, int]]
    linedefs: list[LineDef]
    things: list[tuple[int, int, int, int]] = field(default_factory=list)

    @classmethod
    def load(cls, wad: Wad, mapname: str) -> "Level":
        lumps = ["VERTEXES", "SECTORS", "SIDEDEFS", "LINEDEFS", "THINGS"]
        base = wad.index(mapname)
        found: dict[str, tuple[int, int]] = {}
        for i in range(base + 1, min(base + 12, len(wad.lumps))):
            name, off, size = wad.lumps[i]
            if name in lumps:
                found[name] = (off, size)

        missing = [n for n in lumps if n not in found]
        if missing:
            raise ValueError(f"{mapname}: missing lumps {missing}")

        data = wad._data  # noqa: SLF001 - intentional, read-only access

        off, size = found["VERTEXES"]
        vertices = [struct.unpack_from("<hh", data, off + i * 4) for i in range(size // 4)]

        off, size = found["SECTORS"]
        sectors = []
        for i in range(size // 26):
            fh, ch, fpic, cpic, light, special, tag = struct.unpack_from("<hh8s8sHhh", data, off + i * 26)
            sectors.append(
                Sector(
                    fh,
                    ch,
                    fpic.split(b"\0")[0].decode("latin-1").upper(),
                    cpic.split(b"\0")[0].decode("latin-1").upper(),
                    light,
                    special,
                    tag,
                )
            )

        off, size = found["SIDEDEFS"]
        sidedefs = []
        for i in range(size // 30):
            xo, yo, top, bottom, mid, sector = struct.unpack_from("<hh8s8s8sH", data, off + i * 30)
            sidedefs.append(
                (
                    xo,
                    yo,
                    top.split(b"\0")[0].decode("latin-1").upper(),
                    bottom.split(b"\0")[0].decode("latin-1").upper(),
                    mid.split(b"\0")[0].decode("latin-1").upper(),
                    sector,
                )
            )

        off, size = found["LINEDEFS"]
        linedefs = []
        for i in range(size // 14):
            v1, v2, flags, special, tag, s1, s2 = struct.unpack_from("<hhhhhhh", data, off + i * 14)
            linedefs.append(LineDef(v1, v2, flags, special, tag, (s1 & 0xFFFF, s2 & 0xFFFF)))

        things: list[tuple[int, int, int, int]] = []
        if "THINGS" in found:
            off, size = found["THINGS"]
            for i in range(size // 10):
                x, y, angle, ttype, _flags = struct.unpack_from("<hhhhH", data, off + i * 10)
                things.append((x, y, angle, ttype))

        return cls(mapname, vertices, sectors, sidedefs, linedefs, things)

    # ------------------------------------------------------------------ shapes

    def sector_loops(self, index: int) -> list[list[tuple[int, int]]]:
        """Chain the linedefs that face into a sector into closed loops."""
        segments: list[tuple[int, int]] = []
        for line in self.linedefs:
            for side_index, (v1, v2) in ((0, (line.v1, line.v2)), (1, (line.v2, line.v1))):
                side = line.sides[side_index]
                if side >= len(self.sidedefs):
                    continue
                if self.sidedefs[side][5] == index:
                    segments.append((v1, v2))
        if not segments:
            return []

        by_start: dict[int, list[int]] = {}
        for v1, v2 in segments:
            by_start.setdefault(v1, []).append(v2)

        loops: list[list[tuple[int, int]]] = []
        used: set[tuple[int, int]] = set()
        for start, ends in by_start.items():
            for end in ends:
                if (start, end) in used:
                    continue
                loop = [start]
                used.add((start, end))
                cur = end
                guard = 0
                while cur != start and guard < len(segments) + 4:
                    loop.append(cur)
                    options = [v for v in by_start.get(cur, []) if (cur, v) not in used]
                    if not options:
                        break
                    nxt = options[0]
                    used.add((cur, nxt))
                    cur = nxt
                    guard += 1
                if len(loop) >= 3:
                    loops.append(loop)
        return loops


# Thing type -> (sprite prefix, rotation, label, is_monster)
THING_TYPES: dict[int, tuple[str, int, str, bool]] = {
    1: ("PLAY", 1, "Player 1", False),
    2: ("PLAY", 1, "Player 2", False),
    3: ("PLAY", 1, "Player 3", False),
    4: ("PLAY", 1, "Player 4", False),
    3004: ("POSS", 1, "Zombieman", True),
    9: ("SPOS", 1, "Shotgun guy", True),
    65: ("CPOS", 1, "Chaingunner", True),
    3001: ("TROO", 1, "Imp", True),
    3002: ("SARG", 1, "Demon", True),
    58: ("SARG", 1, "Spectre", True),
    3006: ("SKUL", 1, "Lost soul", True),
    3005: ("HEAD", 1, "Cacodemon", True),
    69: ("BOS2", 1, "Hell knight", True),
    3003: ("BOSS", 1, "Baron of hell", True),
    68: ("BSPI", 1, "Arachnotron", True),
    71: ("PAIN", 1, "Pain elemental", True),
    66: ("SKEL", 1, "Revenant", True),
    67: ("FATT", 1, "Mancubus", True),
    64: ("VILE", 1, "Arch-vile", True),
    7: ("SPID", 1, "Spider mastermind", True),
    16: ("CYBR", 1, "Cyberdemon", True),
    88: ("BOSS", 1, "Boss brain", True),
}


def render_floorplan(
    wad: Wad,
    level: Level,
    size: tuple[int, int] = (512, 320),
    *,
    margin: int = 12,
    monster_sprites: dict[int, Image.Image] | None = None,
    sprite_scale: float = 0.42,
    background: tuple[int, int, int] = (7, 8, 10),
    glow: tuple[int, int, int] = (120, 26, 20),
) -> Image.Image:
    """Draw a top-down floor plan of ``level``."""
    width, height = size
    img = Image.new("RGBA", size, (*background, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    xs = [v[0] for v in level.vertices]
    ys = [v[1] for v in level.vertices]
    if not xs:
        return img
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(1, max_x - min_x)
    span_y = max(1, max_y - min_y)
    usable_w = width - margin * 2
    usable_h = height - margin * 2
    scale = min(usable_w / span_x, usable_h / span_y)
    off_x = margin + (usable_w - span_x * scale) / 2
    off_y = margin + (usable_h - span_y * scale) / 2

    def to_px(v: tuple[int, int]) -> tuple[float, float]:
        return (off_x + (v[0] - min_x) * scale, off_y + (max_y - v[1]) * scale)

    for index, sector in enumerate(level.sectors):
        loops = level.sector_loops(index)
        if not loops:
            continue
        try:
            flat = wad.flat(sector.floor_pic)
            base = average_color(flat)
        except Exception:
            base = (90, 70, 60)
        light = 0.28 + 0.72 * (sector.light / 255.0)
        color = tuple(int(min(255, c * light * 1.15)) for c in base)
        for loop in loops:
            points = [to_px(level.vertices[v]) for v in loop]
            draw.polygon(points, fill=(*color, 205))

    # Sector outlines.
    for line in level.linedefs:
        a = to_px(level.vertices[line.v1])
        b = to_px(level.vertices[line.v2])
        two_sided = line.sides[1] != 0xFFFF
        color = (*glow, 90) if two_sided else (255, 235, 210, 120)
        draw.line([a, b], fill=color, width=1)

    # Monster markers.
    if monster_sprites:
        for x, y, _angle, ttype in level.things:
            info = THING_TYPES.get(ttype)
            if info is None:
                continue
            sprite = monster_sprites.get(ttype)
            if sprite is None:
                continue
            px, py = to_px((x, y))
            sw = max(8, int(sprite.width * scale * sprite_scale * 2.2))
            sh = max(8, int(sprite.height * scale * sprite_scale * 2.2))
            sw = min(sw, 46)
            sh = min(sh, 46)
            glyph = sprite.resize((sw, sh), Image.NEAREST)
            img.alpha_composite(glyph, (int(px - sw / 2), int(py - sh / 2)))

    glow_layer = img.filter(ImageFilter.GaussianBlur(6))
    img = Image.blend(img, glow_layer, 0.28)

    # Frame + grid.
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle([0, 0, width - 1, height - 1], outline=(150, 40, 30, 160), width=1)
    draw.rectangle([3, 3, width - 4, height - 4], outline=(20, 20, 22, 255), width=1)
    return img