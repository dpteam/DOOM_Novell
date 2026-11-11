"""WAD reading primitives used by the DOOM_Novell asset pipeline.

The module knows just enough about the classic DOOM formats to pull
paletted graphics, flats, textures, sprites, sounds and level geometry
out of any IWAD (``DOOM2.WAD``, ``FREEDOOM2.WAD``, ``freedoom1.wad``...).

Everything is pure Python plus Pillow; no external tools required.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image

__all__ = [
    "Wad",
    "WadError",
    "TextureDef",
    "raw_patch",
    "decode_patch",
]

MARKER_PAIRS = {
    "patches": (("P_START", "P_END"), ("P1_START", "P1_END"), ("PP_START", "PP_END")),
    "flats": (
        ("F_START", "F_END"),
        ("F1_START", "F1_END"),
        ("F2_START", "F2_END"),
        ("FF_START", "FF_END"),
    ),
    "sprites": (("S_START", "S_END"), ("SS_START", "SS_END")),
}


class WadError(RuntimeError):
    """Raised when a WAD (or a requested lump) cannot be parsed."""


@dataclass(frozen=True)
class TextureDef:
    name: str
    width: int
    height: int
    patches: tuple[tuple[int, int, str], ...]


class Wad:
    """A read-only view over a WAD file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data = self.path.read_bytes()
        if len(self._data) < 12:
            raise WadError(f"{self.path.name}: file is too short to be a WAD")

        magic, numlumps, diroffset = struct.unpack_from("<4sii", self._data, 0)
        self.magic = magic.decode("latin-1")
        if self.magic not in ("IWAD", "PWAD"):
            raise WadError(f"{self.path.name}: unexpected magic {self.magic!r}")
        self.numlumps = numlumps

        self.lumps: list[tuple[str, int, int]] = []
        self._byname: dict[str, list[int]] = {}
        for i in range(numlumps):
            off, size, raw_name = struct.unpack_from("<ii8s", self._data, diroffset + i * 16)
            name = raw_name.split(b"\0")[0].decode("latin-1").upper()
            self.lumps.append((name, off, size))
            self._byname.setdefault(name, []).append(i)

        self._palette: bytes | None = None
        self._colormap: bytes | None = None
        self._pnames: list[str] | None = None
        self._textures: dict[str, TextureDef] | None = None
        self._sprite_names: list[str] | None = None
        self._flat_names: list[str] | None = None
        self._light_cache: dict[int, bytes] = {}
        self._texture_cache: dict[tuple[str, int], Image.Image] = {}
        self._patch_cache: dict[tuple[str, int], Image.Image] = {}

    # ------------------------------------------------------------------ lumps

    def __contains__(self, name: str) -> bool:
        return name.upper() in self._byname

    @property
    def names(self) -> list[str]:
        return [n for n, _, _ in self.lumps]

    def index(self, name: str, occurrence: int = 0) -> int:
        hits = self._byname.get(name.upper())
        if not hits:
            raise WadError(f"{self.path.name}: missing lump {name!r}")
        try:
            return hits[occurrence]
        except IndexError:
            raise WadError(f"{self.path.name}: lump {name!r} has only {len(hits)} copies") from None

    def entry(self, name: str, occurrence: int = 0) -> tuple[int, int]:
        _, off, size = self.lumps[self.index(name, occurrence)]
        return off, size

    def bytes(self, name: str, occurrence: int = 0) -> bytes:
        off, size = self.entry(name, occurrence)
        return self._data[off : off + size]

    def find(self, prefix: str) -> list[str]:
        prefix = prefix.upper()
        return [n for n, _, _ in self.lumps if n.startswith(prefix)]

    def namespace(self, kind: str) -> list[str]:
        """Names between the marker lumps of ``kind`` (patches/flats/sprites)."""
        pairs = MARKER_PAIRS[kind]
        out: list[str] = []
        for start, end in pairs:
            if start not in self._byname:
                continue
            begin = self.index(start)
            stop = self.index(end)
            for name, _, _ in self.lumps[begin + 1 : stop]:
                if name and not name.endswith(("_START", "_END")):
                    out.append(name)
        return out

    @property
    def sprite_names(self) -> list[str]:
        if self._sprite_names is None:
            self._sprite_names = self.namespace("sprites")
        return self._sprite_names

    @property
    def flat_names(self) -> list[str]:
        if self._flat_names is None:
            self._flat_names = self.namespace("flats")
        return self._flat_names

    # ---------------------------------------------------------------- palette

    @property
    def palette(self) -> bytes:
        if self._palette is None:
            self._palette = self.bytes("PLAYPAL")[:768]
        return self._palette

    @property
    def colormap(self) -> bytes:
        if self._colormap is None:
            self._colormap = self.bytes("COLORMAP")
        return self._colormap

    def palette_table(self, light: int = 0) -> bytes:
        """256*3 RGB bytes after applying COLORMAP row ``light`` (0 = bright)."""
        light = max(0, min(33, int(light)))
        if light not in self._light_cache:
            cm = self.colormap
            row = cm[light * 256 : light * 256 + 256]
            pal = self.palette
            table = bytearray(768)
            for i in range(256):
                src = row[i] * 3
                table[i * 3 : i * 3 + 3] = pal[src : src + 3]
            self._light_cache[light] = bytes(table)
        return self._light_cache[light]

    def colorize(self, indices: bytes, width: int, height: int, light: int = 0, alpha=None) -> Image.Image:
        """Turn raw palette indices into an RGBA image."""
        table = self.palette_table(light)
        rgb = bytearray(width * height * 3)
        for i, idx in enumerate(indices):
            rgb[i * 3 : i * 3 + 3] = table[idx * 3 : idx * 3 + 3]
        img = Image.frombytes("RGB", (width, height), bytes(rgb)).convert("RGBA")
        if alpha is not None:
            img.putalpha(alpha)
        return img

    # ------------------------------------------------------------------ PATCH

    def raw_patch(self, name: str) -> tuple[int, int, int, int, list[list[int | None]]]:
        return raw_patch(self.bytes(name))

    def patch(self, name: str, light: int = 0) -> Image.Image:
        key = (name.upper(), light)
        cached = self._patch_cache.get(key)
        if cached is not None:
            return cached

        w, h, _left, _top, rows = self.raw_patch(name)
        table = self.palette_table(light)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = img.load()
        for x in range(w):
            col = rows[x]
            for y in range(h):
                idx = col[y]
                if idx is None:
                    continue
                px[x, y] = (*table[idx * 3 : idx * 3 + 3], 255)
        self._patch_cache[key] = img
        return img

    # ---------------------------------------------------------------- TEXTURES

    @property
    def pnames(self) -> list[str]:
        if self._pnames is None:
            data = self.bytes("PNAMES")
            (count,) = struct.unpack_from("<i", data, 0)
            names = []
            for i in range(count):
                raw = data[4 + i * 8 : 12 + i * 8]
                names.append(raw.split(b"\0")[0].decode("latin-1").upper())
            self._pnames = names
        return self._pnames

    @property
    def textures(self) -> dict[str, TextureDef]:
        if self._textures is None:
            textures: dict[str, TextureDef] = {}
            for lump in ("TEXTURE1", "TEXTURE2"):
                if lump not in self._byname:
                    continue
                data = self.bytes(lump)
                (count,) = struct.unpack_from("<i", data, 0)
                offsets = struct.unpack_from(f"<{count}i", data, 4)
                for off in offsets:
                    name, _masked, w, h, _coldir, pcount = struct.unpack_from("<8sihhih", data, off)
                    patches = []
                    for p in range(pcount):
                        px, py, pidx, _step, _cmap = struct.unpack_from("<hhhhh", data, off + 22 + p * 10)
                        patches.append((px, py, self.pnames[pidx]))
                    key = name.split(b"\0")[0].decode("latin-1").upper()
                    textures[key] = TextureDef(key, w, h, tuple(patches))
            self._textures = textures
        return self._textures

    def texture(self, name: str, light: int = 0) -> Image.Image:
        """Composite a wall texture out of its patches."""
        name = name.upper()
        key = (name, light)
        cached = self._texture_cache.get(key)
        if cached is not None:
            return cached

        if name not in self.textures:
            raise WadError(f"{self.path.name}: no texture named {name!r}")
        tex = self.textures[name]
        img = Image.new("RGBA", (tex.width, tex.height), (0, 0, 0, 255))
        for ox, oy, pname in tex.patches:
            try:
                patch = self.patch(pname, light)
            except WadError:
                continue
            _blit(img, patch, ox, oy)
        self._texture_cache[key] = img
        return img

    # ------------------------------------------------------------------- FLAT

    def flat(self, name: str, light: int = 0) -> Image.Image:
        name = name.upper()
        data = self.bytes(name)
        if len(data) == 64 * 64:
            w = h = 64
        elif len(data) == 128 * 128:
            w = h = 128
        else:
            side = int(len(data) ** 0.5)
            w = h = side
        return self.colorize(data[: w * h], w, h, light)

    # ----------------------------------------------------------------- SPRITE

    def sprite(self, name: str, light: int = 0) -> Image.Image:
        return self.patch(name.upper(), light)

    def sprite_frames(self, prefix: str, rotation: int = 1) -> dict[str, Image.Image]:
        """All frames of a sprite whose lump name ends with ``rotation``."""
        suffix = str(rotation)
        out: dict[str, Image.Image] = {}
        for lump in self.sprite_names:
            if lump.startswith(prefix.upper()) and len(lump) == 6 and lump[5] == suffix:
                out[lump[4]] = self.sprite(lump)
        return out

    # ------------------------------------------------------------------ misc

    def banner(self) -> str:
        total = sum(size for _, _, size in self.lumps)
        return f"{self.path.name}: {self.magic}, {self.numlumps} lumps, {total / 1048576:.2f} MiB"


def raw_patch(data: bytes) -> tuple[int, int, int, int, list[list[int | None]]]:
    """Decode the column/post format used by DOOM graphics lumps."""
    if len(data) < 8:
        raise WadError("patch too short")
    width, height, left, top = struct.unpack_from("<hhhh", data, 0)
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        raise WadError(f"implausible patch size {width}x{height}")
    colofs = struct.unpack_from(f"<{width}I", data, 8)

    rows: list[list[int | None]] = [[None] * height for _ in range(width)]
    for x, offset in enumerate(colofs):
        if offset == 0xFFFFFFFF or offset >= len(data):
            continue
        pos = offset
        while pos < len(data):
            topdelta = data[pos]
            pos += 1
            if topdelta == 0xFF:
                break
            if pos + 1 >= len(data):
                break
            length = data[pos]
            pos += 2  # skip length byte plus the unused padding byte
            for i in range(length):
                y = topdelta + i
                if 0 <= y < height and pos + i < len(data):
                    rows[x][y] = data[pos + i]
            pos += length + 1
    return width, height, left, top, rows


def decode_patch(data: bytes, palette_table: bytes) -> Image.Image:
    w, h, _left, _top, rows = raw_patch(data)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for x in range(w):
        col = rows[x]
        for y in range(h):
            idx = col[y]
            if idx is None:
                continue
            px[x, y] = (*palette_table[idx * 3 : idx * 3 + 3], 255)
    return img


def _blit(dst: Image.Image, src: Image.Image, x: int, y: int) -> None:
    """Alpha-blit ``src`` onto ``dst`` at (x, y), clipping negative origins."""
    dx0, dy0 = max(0, x), max(0, y)
    sx0, sy0 = dx0 - x, dy0 - y
    w = min(src.width - sx0, dst.width - dx0)
    h = min(src.height - sy0, dst.height - dy0)
    if w <= 0 or h <= 0:
        return
    dst.alpha_composite(src.crop((sx0, sy0, sx0 + w, sy0 + h)), (dx0, dy0))


def tile(img: Image.Image, size: tuple[int, int], offset: tuple[int, int] = (0, 0)) -> Image.Image:
    """Tile ``img`` to fill ``size`` starting at ``offset``."""
    out = Image.new("RGBA", size)
    step_x, step_y = img.size
    ox = -(offset[0] % step_x)
    oy = -(offset[1] % step_y)
    for y in range(oy, size[1], step_y):
        for x in range(ox, size[0], step_x):
            out.paste(img, (x, y))
    return out


def average_color(img: Image.Image, box: Sequence[int] | None = None) -> tuple[int, int, int]:
    region = img.convert("RGB")
    if box is not None:
        region = region.crop(tuple(box))  # type: ignore[arg-type]
    small = region.resize((1, 1), Image.BOX)
    return small.getpixel((0, 0))


def iter_sprite_frames(names: Iterable[str]) -> dict[str, list[str]]:
    """Group sprite lump names by their 4-letter sprite prefix."""
    groups: dict[str, list[str]] = {}
    for name in names:
        if len(name) < 5:
            continue
        groups.setdefault(name[:4], []).append(name)
    return groups