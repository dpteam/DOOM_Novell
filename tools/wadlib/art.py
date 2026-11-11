"""Procedural art assembly: every pixel here comes out of the IWAD.

The pipeline builds three kinds of images:

* ``compose_scene``   - a 1280x720 "stage" backdrop made of real wall
  textures, flats and sprite props;
* ``plate``           - UI panels (textbox, buttons, frames) milled from
  wall textures with a bevel and rivets;
* ``title_screen``    - the TITLEPIC / M_DOOM poster used by the main menu.

Everything is deterministic: the same IWAD always produces the same art.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from .wadfile import Wad, average_color, tile

__all__ = [
    "SceneSpec",
    "compose_scene",
    "plate",
    "title_screen",
    "vignette",
    "scanlines",
    "add_grain",
    "scale_nearest",
    "sprite_on_stage",
]

W, H = 1280, 720


# --------------------------------------------------------------------- basics


def scale_nearest(img: Image.Image, factor: float) -> Image.Image:
    size = (max(1, int(img.width * factor)), max(1, int(img.height * factor)))
    return img.resize(size, Image.NEAREST)


def _rgba(img: Image.Image) -> Image.Image:
    return img if img.mode == "RGBA" else img.convert("RGBA")


def _tiled_texture(wad: Wad, name: str, size: tuple[int, int], *, light: int = 0, zoom: int = 2) -> Image.Image:
    """Wall texture, nearest-upscaled and tiled to ``size``."""
    tex = wad.texture(name, light)
    if zoom != 1:
        tex = scale_nearest(tex, zoom)
    return tile(tex, size)


def _tiled_flat(wad: Wad, name: str, size: tuple[int, int], *, light: int = 0, zoom: int = 3) -> Image.Image:
    flat = wad.flat(name, light)
    if zoom != 1:
        flat = scale_nearest(flat, zoom)
    return tile(flat, size)


def _gradient(size: tuple[int, int], vertical: bool, start: float, end: float) -> Image.Image:
    """A grayscale gradient usable as a brightness multiplier.

    ``start`` is the brightness at the top/left edge, ``end`` at the
    bottom/right edge, both in 0..1.
    """
    w, h = size
    if vertical:
        ramp = np.linspace(start, end, h, dtype=np.float32)
        grid = np.tile(ramp[:, None], (1, w))
    else:
        ramp = np.linspace(start, end, w, dtype=np.float32)
        grid = np.tile(ramp[None, :], (h, 1))
    data = (np.clip(grid, 0.0, 1.0) * 255).astype(np.uint8)
    return Image.frombytes("L", (w, h), data.tobytes())


def _multiply(img: Image.Image, mask: Image.Image) -> Image.Image:
    """Multiply an RGBA image by a grayscale mask, keeping its alpha."""
    alpha = img.getchannel("A")
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    graded = ImageChops.multiply(img.convert("RGB"), mask_rgb).convert("RGBA")
    graded.putalpha(alpha)
    return graded


def tint(img: Image.Image, color: tuple[int, int, int], strength: float) -> Image.Image:
    layer = Image.new("RGBA", img.size, (*color, 255))
    return Image.blend(_rgba(img), layer, strength)


def vignette(size: tuple[int, int], strength: float = 0.82, power: float = 2.4) -> Image.Image:
    w, h = size
    small = Image.new("L", (64, 36), 0)
    px = small.load()
    for y in range(36):
        for x in range(64):
            dx = (x - 31.5) / 31.5
            dy = (y - 17.5) / 17.5
            d = min(1.0, (dx * dx * 0.85 + dy * dy) ** 0.5)
            px[x, y] = int(255 * max(0.0, 1.0 - strength * (d ** power)))
    return small.resize(size, Image.BICUBIC)


def scanlines(size: tuple[int, int], step: int = 3, alpha: int = 30) -> Image.Image:
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    return layer


def add_grain(img: Image.Image, amount: int = 7, seed: int = 1) -> Image.Image:
    """Add luminance noise in place of a flat overlay (keeps alpha)."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(img).astype(np.int16)
    noise = rng.integers(-amount, amount + 1, size=(arr.shape[0], arr.shape[1], 1), dtype=np.int16)
    arr[..., :3] = np.clip(arr[..., :3] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


# ----------------------------------------------------------------------- props


def sprite_on_stage(
    wad: Wad,
    lump: str,
    scale: float,
    *,
    shadow: bool = True,
    light: int = 0,
) -> Image.Image:
    """A sprite (with an optional contact shadow baked in)."""
    sprite = scale_nearest(wad.sprite(lump, light), scale)
    if not shadow:
        return sprite

    canvas = Image.new("RGBA", (sprite.width, sprite.height + int(sprite.height * 0.12)), (0, 0, 0, 0))
    shadow_h = int(sprite.height * 0.12)
    ellipse = Image.new("RGBA", (sprite.width, shadow_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ellipse)
    draw.ellipse([0, 0, sprite.width - 1, shadow_h - 1], fill=(0, 0, 0, 150))
    ellipse = ellipse.filter(ImageFilter.GaussianBlur(max(1, shadow_h // 3)))
    canvas.alpha_composite(ellipse, (0, sprite.height - shadow_h // 2))
    canvas.alpha_composite(sprite, (0, 0))
    return canvas


# ----------------------------------------------------------------------- scene


@dataclass
class SceneSpec:
    key: str
    wall: str
    side: str
    floor: str
    ceiling: str
    accent: tuple[int, int, int] = (150, 40, 26)
    # Fractions of the frame: x0, y0, x1, y1 of the back wall.
    back: tuple[float, float, float, float] = (0.20, 0.12, 0.80, 0.76)
    portal: str = "door"  # door | none
    door: str = "wall"  # texture name, or "wall" to reuse spec.wall
    door_width: float = 0.11
    door_height: float = 0.48
    blood: bool = False
    props: list[tuple[str, float, float, float]] = field(default_factory=list)
    grade: tuple[float, float, float] = (1.0, 1.0, 1.0)
    fog: float = 0.05
    seed: int = 1
    zoom: int = 2


def compose_scene(wad: Wad, spec: SceneSpec) -> Image.Image:
    """Build a stage backdrop from wall textures, flats and sprite props."""
    img = Image.new("RGBA", (W, H), (6, 6, 8, 255))
    x0f, y0f, x1f, y1f = spec.back
    x0, y0, x1, y1 = int(x0f * W), int(y0f * H), int(x1f * W), int(y1f * H)

# --- back wall -----------------------------------------------------
    ac = spec.accent
    back = _tiled_texture(wad, spec.wall, (x1 - x0, y1 - y0), light=0, zoom=spec.zoom)
    back = _multiply(back, _gradient(back.size, True, 0.95, 0.52))
    img.alpha_composite(back, (x0, y0))

    # --- ceiling -------------------------------------------------------
    if y0 > 0:
        ceil = _tiled_flat(wad, spec.ceiling, (W, y0), light=0, zoom=3)
        ceil = _multiply(ceil, _gradient(ceil.size, True, 0.26, 0.55))
        img.alpha_composite(ceil, (0, 0))

    # --- floor ---------------------------------------------------------
    floor_h = H - y1
    if floor_h > 0:
        floor = _tiled_flat(wad, spec.floor, (W, floor_h), light=0, zoom=3)
        floor = _multiply(floor, _gradient(floor.size, True, 0.32, 0.95))
        img.alpha_composite(floor, (0, y1))

    # --- side walls ----------------------------------------------------
    side_w = max(1, x0)
    side_tex = _tiled_texture(wad, spec.side, (side_w, H), light=0, zoom=spec.zoom)
    left = _multiply(side_tex, _gradient(side_tex.size, False, 0.20, 0.98))
    right = left.transpose(Image.FLIP_LEFT_RIGHT)
    img.alpha_composite(left, (0, 0))
    img.alpha_composite(right, (W - side_w, 0))

    # --- doorway -------------------------------------------------------
    cx = (x0 + x1) // 2
    half = max(30, int((x1 - x0) * spec.door_width) // 2)
    door_top = y1 - int((y1 - y0) * spec.door_height)
    door = (cx - half, door_top, cx + half, y1)

    # Recess shadow behind the frame.
    recess = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(recess).rectangle(
        [door[0] - 12, door[1] - 12, door[2] + 12, door[3]], fill=(0, 0, 0, 150)
    )
    img.alpha_composite(recess.filter(ImageFilter.GaussianBlur(7)))

    if spec.portal != "none":
        door_tex = spec.wall if spec.door == "wall" else spec.door
        door_img = _tiled_texture(wad, door_tex, (door[2] - door[0], door[3] - door[1]), light=0, zoom=spec.zoom)
        door_img = _multiply(door_img, _gradient(door_img.size, True, 0.40, 0.80))
        img.alpha_composite(door_img, (door[0], door[1]))

    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.rectangle(
        [door[0] - 4, door[1] - 4, door[2] + 4, door[3]],
        outline=(16, 16, 18, 255),
        width=4,
    )
    fd.rectangle(door, outline=(236, 226, 208, 70), width=1)
    fd.line([(door[0], door[1]), (door[2], door[1])], fill=(*ac, 190), width=2)
    img.alpha_composite(frame)

    # --- light spill ---------------------------------------------------
    spill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(spill)
    pool_w = int((door[2] - door[0]) * 2.4)
    sd.ellipse(
        [cx - pool_w, y1 - 26, cx + pool_w, y1 + floor_h * 0.9],
        fill=(*ac, 70),
    )
    sd.rectangle([door[0], door[1] - 3, door[2], door[1] + 1], fill=(*ac, 220))
    img.alpha_composite(spill.filter(ImageFilter.GaussianBlur(18)))

    # --- wall lamps ------------------------------------------------------
    lamps = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lamps)
    for lx in (x0 + int((x1 - x0) * 0.11), x1 - int((x1 - x0) * 0.11)):
        ly = y0 + int((y1 - y0) * 0.10)
        ld.rectangle([lx - 7, ly, lx + 7, ly + 46], fill=(250, 244, 226, 235))
        ld.rectangle([lx - 11, ly - 6, lx + 11, ly], fill=(24, 24, 26, 255))
        ld.rectangle([lx - 11, ly + 46, lx + 11, ly + 51], fill=(24, 24, 26, 255))
    img.alpha_composite(lamps.filter(ImageFilter.GaussianBlur(1.2)))
    img.alpha_composite(lamps.filter(ImageFilter.GaussianBlur(26)))

    # --- props -----------------------------------------------------------
    for lump, fx, fy, factor in spec.props:
        try:
            prop = sprite_on_stage(wad, lump, factor)
        except Exception:
            continue
        px = int(fx * W - prop.width / 2)
        py = int(fy * H - prop.height)
        img.alpha_composite(prop, (px, py))

    # --- blood / grime ---------------------------------------------------
    if spec.blood:
        rng = random.Random(spec.seed * 31 + 7)
        decal = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(decal)
        for _ in range(9):
            bx = rng.randint(int(W * 0.05), int(W * 0.95))
            by = rng.randint(int(H * 0.55), int(H * 0.97))
            size = rng.randint(18, 70)
            dd.ellipse([bx, by, bx + size, by + int(size * 0.45)], fill=(96, 8, 10, rng.randint(90, 160)))
        img.alpha_composite(decal.filter(ImageFilter.GaussianBlur(3)))

    # --- grade + atmosphere ----------------------------------------------
    if spec.fog > 0:
        fog = Image.new("RGBA", (W, H), (*ac, 255))
        fog.putalpha(int(255 * spec.fog))
        img = Image.alpha_composite(img, fog)

    r, g, b = spec.grade
    if (r, g, b) != (1.0, 1.0, 1.0):
        chans = img.split()
        img = Image.merge(
            "RGBA",
            (
                chans[0].point(lambda v: min(255, int(v * r))),
                chans[1].point(lambda v: min(255, int(v * g))),
                chans[2].point(lambda v: min(255, int(v * b))),
                chans[3],
            ),
        )

    img = _multiply(img, vignette((W, H), strength=0.80, power=2.6))
    img.alpha_composite(scanlines((W, H), 3, 22))
    img = add_grain(img, 6, spec.seed)

    # A hair of bloom so highlights read as light, not paint.
    bloom = img.filter(ImageFilter.GaussianBlur(9))
    img = Image.blend(img, bloom, 0.16)
    return img


# ------------------------------------------------------------------------ UI


def plate(
    wad: Wad,
    texture: str,
    size: tuple[int, int],
    *,
    brightness: float = 0.62,
    alpha: int = 255,
    bevel: bool = True,
    rivets: bool = True,
    border: tuple[int, int, int] = (12, 12, 14),
    highlight: tuple[int, int, int] = (255, 236, 210),
    zoom: int = 2,
    tint_color: tuple[int, int, int] | None = None,
    seed: int = 3,
    kind: str = "texture",
    shade: float = 0.0,
    red: bool = False,
) -> Image.Image:
    """A UI panel: textured metal with a bevel, corner rivets and grime."""
    w, h = size
    if kind == "flat":
        body = _tiled_flat(wad, texture, (w, h), light=0, zoom=max(2, zoom))
    else:
        body = _tiled_texture(wad, texture, (w, h), light=0, zoom=zoom)
    body = ImageEnhance.Brightness(body).enhance(brightness)
    if tint_color is not None:
        body = Image.blend(body, Image.new("RGBA", (w, h), (*tint_color, 255)), 0.25)
    body = add_grain(body, 5, seed)

    if red:
        body = tint(body, (110, 12, 8), 0.18)

    if shade > 0:
        # Black gradient over the panel so dialogue text keeps its contrast.
        shade_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        ramp = (np.linspace(0.0, shade, h) ** 1.4 * 255).astype(np.uint8)
        arr[..., 3] = ramp[:, None]
        body = Image.alpha_composite(body, Image.fromarray(arr, "RGBA"))
        del shade_layer

    if bevel:
        draw = ImageDraw.Draw(body)
        draw.rectangle([0, 0, w - 1, h - 1], outline=(*border, 255), width=2)
        draw.line([(2, 2), (w - 3, 2)], fill=(*highlight, 70), width=1)
        draw.line([(2, 2), (2, h - 3)], fill=(*highlight, 55), width=1)
        draw.line([(2, h - 3), (w - 3, h - 3)], fill=(0, 0, 0, 150), width=1)
        draw.line([(w - 3, 2), (w - 3, h - 3)], fill=(0, 0, 0, 150), width=1)
        inner = 5
        if w > inner * 2 + 4 and h > inner * 2 + 4:
            draw.rectangle([inner, inner, w - inner - 1, h - inner - 1], outline=(0, 0, 0, 60), width=1)

    if rivets and w > 26 and h > 26:
        draw = ImageDraw.Draw(body)
        for cx, cy in ((7, 7), (w - 8, 7), (7, h - 8), (w - 8, h - 8)):
            draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(46, 44, 42, 255), outline=(8, 8, 8, 255))
            draw.point((cx - 1, cy - 1), fill=(*highlight, 200))
            draw.point((cx + 1, cy + 1), fill=(0, 0, 0, 200))

    if alpha < 255:
        a = body.getchannel("A").point(lambda v: v * alpha // 255)
        body.putalpha(a)
    return body


def title_screen(wad: Wad, *, brightness: float = 0.62) -> Image.Image:
    """The main-menu poster: TITLEPIC fitted to 1280x720 with a red grade."""
    pic = wad.patch("TITLEPIC") if "TITLEPIC" in wad else None
    if pic is None:
        img = Image.new("RGBA", (W, H), (10, 8, 8, 255))
    else:
        sharp = scale_nearest(pic, H / pic.height)
        if sharp.width >= W:
            left = (sharp.width - W) // 2
            img = sharp.crop((left, 0, left + W, H))
        else:
            # Fill the sides with a blurred, darkened blow-up of the poster.
            cover = pic.resize((W, max(H, int(pic.height * W / pic.width))), Image.NEAREST)
            top = (cover.height - H) // 2
            cover = cover.crop((0, top, W, top + H)).filter(ImageFilter.GaussianBlur(14))
            cover = ImageEnhance.Brightness(cover).enhance(0.45)
            img = cover
            img.alpha_composite(sharp, ((W - sharp.width) // 2, 0))

    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = tint(img, (150, 30, 20), 0.20)
    img = _multiply(img, vignette((W, H), 0.9, 1.9))
    img.alpha_composite(scanlines((W, H), 3, 40))
    img = add_grain(img, 8, 11)

    # A dark band along the bottom so the menu text stays readable.
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for i in range(H // 2):
        a = int(150 * (i / (H / 2)) ** 2)
        bd.line([(0, H // 2 + i), (W, H // 2 + i)], fill=(0, 0, 0, a))
    img.alpha_composite(band)
    return img


def logo(wad: Wad, name: str, height: int, *, palette_light: int = 0) -> Image.Image:
    """A big WAD patch (``M_DOOM``-style logo) scaled to ``height`` pixels."""
    patch = wad.patch(name, palette_light)
    factor = height / patch.height
    return scale_nearest(patch, factor)


def nine_slice_safe(img: Image.Image) -> Image.Image:
    """Placeholder for future nine-slice work; returns the image unchanged."""
    return img


def save_ico(img: Image.Image, path: Path, sizes: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="ICO", sizes=[(s, s) for s in sizes])


def write_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def avg_flat_color(wad: Wad, name: str) -> tuple[int, int, int]:
    return average_color(wad.flat(name))
