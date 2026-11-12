"""Build every asset for DOOM_Novell out of a single IWAD.

    python tools/build_assets.py --iwad "doom2.wad"

Works with DOOM2.WAD, FREEDOOM2.WAD, doom.wad / FREEDOOM1.WAD.  The
output goes into ``game/`` in the format Ren'Py expects: GUI images,
backgrounds, character sprites, a BMFont pair, sounds, rendered music and
a manifest describing exactly which lumps were used.

No network, no WAD editors, no external audio tools (ffmpeg is used only
if present, to shrink the rendered music to OGG).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

from wadlib import audio as wad_audio  # noqa: E402
from wadlib.art import (  # noqa: E402
    SceneSpec,
    add_grain,
    compose_scene,
    logo,
    plate,
    save_ico,
    scale_nearest,
    scanlines,
    sprite_on_stage,
    title_screen,
    vignette,
    write_png,
)
from wadlib.fonts import patch_font, read_metrics, ttf_font  # noqa: E402
from wadlib.mapdata import Level, THING_TYPES, render_floorplan  # noqa: E402
from wadlib.wadfile import Wad, WadError  # noqa: E402

TOOL_VERSION = "1.0.0"

# --------------------------------------------------------------------- config

CHARACTERS: dict[str, dict] = {
    "boris": {"sprite": "POSS", "height": 400, "label": "Борис"},
    "imp": {"sprite": "TROO", "height": 330, "label": "Игнат"},
    "caco": {"sprite": "HEAD", "height": 340, "label": "Алексей"},
    "baron": {"sprite": "BOSS", "height": 520, "label": "Барон"},
    "revenant": {"sprite": "SKEL", "height": 500, "label": "Роман"},
    "archvile": {"sprite": "VILE", "height": 500, "label": "Вика"},
    "cyber": {"sprite": "CYBR", "height": 640, "label": "Кибердемон"},
    "lost": {"sprite": "SKUL", "height": 190, "label": "Душа"},
    "pain": {"sprite": "PAIN", "height": 280, "label": "Боль"},
    "mancubus": {"sprite": "FATT", "height": 500, "label": "Повар"},
    "arachno": {"sprite": "BSPI", "height": 300, "label": "Арахна"},
    "spider": {"sprite": "SPID", "height": 540, "label": "Паучиха"},
    "chaingunner": {"sprite": "CPOS", "height": 400, "label": "Охранник"},
    "shotgunner": {"sprite": "SPOS", "height": 400, "label": "Конвоир"},
    "demon": {"sprite": "SARG", "height": 360, "label": "Пёс"},
}

MOODS: dict[str, list[str]] = {
    "neutral": ["A1"],
    "talk": ["B1", "A1"],
    "angry": ["F1", "E1", "B1", "A1"],
    "pain": ["H1", "G1", "A1"],
    "dead": ["L1", "K1", "J1", "I1", "A1"],
}

ITEM_SPRITES = {
    "medikit": "MEDIA0",
    "stimpack": "STIMA0",
    "soulsphere": "BON1A0",
    "armor_bonus": "BON2A0",
    "green_armor": "ARM1A0",
    "megaarmor": "MEGAA0",
    "chainsaw": "SAWGA0",
    "pistol": "PISGA0",
    "shotgun": "SHOTA0",
    "supershotgun": "SHT2A0",
    "chaingun": "CHGGA0",
    "plasma": "PLASA0",
    "bfg": "BFUGA0",
    "rocket": "ROCKA0",
    "blue_key": "BKEYA0",
    "red_key": "RKEYA0",
    "yellow_key": "YKEYA0",
    "barrel": "BAR1A0",
}

PROP_SPRITES = {
    "barrel": "BAR1A0",
    "barrel_hit": "BAR1B0",
    "lamp": "COLUA0",
    "skullpole": "POL3A0",
    "skullpole2": "POL3B0",
    "corpse": "POL5A0",
    "blood": "BLUDA0",
    "blood2": "BLUDC0",
}

# key -> (label, wall, side, floor, ceiling, door, accent, grade, blood)
SCENES: dict[str, dict] = {
    "landing": dict(
        label="Приёмная",
        wall="STARTAN3",
        side="SUPPORT2",
        floor="FLOOR4_8",
        ceiling="CEIL3_5",
        door="BIGDOOR1",
        accent=(96, 170, 205),
        props=[("COLUA0", 0.14, 0.94, 4.6), ("BAR1A0", 0.86, 0.96, 4.2)],
    ),
    "office": dict(
        label="Открытый офис",
        wall="STARTAN2",
        side="BROWN1",
        floor="FLOOR0_1",
        ceiling="FLAT5",
        door="DOOR1",
        accent=(205, 190, 140),
        props=[("COLUA0", 0.12, 0.95, 4.2), ("BAR1A0", 0.9, 0.97, 3.8)],
    ),
    "corridor": dict(
        label="Коридор",
        wall="STARTAN3",
        side="SUPPORT3",
        floor="FLOOR4_6",
        ceiling="CEIL4_2",
        door="BIGDOOR4",
        accent=(120, 160, 200),
        back=(0.18, 0.10, 0.82, 0.78),
        props=[("POL5A0", 0.2, 0.98, 3.2), ("BAR1B0", 0.8, 0.96, 4.0)],
    ),
    "server": dict(
        label="Серверная",
        wall="COMPSTA1",
        side="TEKWALL4",
        floor="FLOOR1_1",
        ceiling="CEIL3_2",
        door="BIGDOOR6",
        accent=(70, 200, 190),
        grade=(0.9, 1.05, 1.05),
        props=[("COLUA0", 0.16, 0.94, 4.0)],
    ),
    "canteen": dict(
        label="Столовая",
        wall="BROWNGRN",
        side="BROWN1",
        floor="FLOOR5_4",
        ceiling="CEIL5_1",
        door="BIGDOOR2",
        accent=(220, 180, 110),
        props=[("BAR1A0", 0.15, 0.96, 4.0), ("BAR1B0", 0.86, 0.98, 3.6)],
    ),
    "hellgate": dict(
        label="Врата",
        wall="MARBLE1",
        side="SKIN2",
        floor="FLOOR7_2",
        ceiling="FLAT1",
        door="BIGDOOR7",
        accent=(205, 70, 30),
        grade=(1.12, 0.95, 0.88),
        blood=True,
        props=[("POL3A0", 0.15, 0.95, 4.0), ("POL3B0", 0.85, 0.97, 3.6)],
    ),
    "hellhall": dict(
        label="Адский опенспейс",
        wall="MARBLE3",
        side="SKINEDGE",
        floor="FLAT22",
        ceiling="FLAT14",
        door="BIGDOOR5",
        accent=(220, 90, 40),
        grade=(1.15, 0.92, 0.85),
        blood=True,
        back=(0.16, 0.10, 0.84, 0.77),
        props=[("POL3A0", 0.12, 0.96, 4.4), ("POL5A0", 0.88, 0.98, 3.4)],
    ),
    "temple": dict(
        label="Храм отчётности",
        wall="WOOD1",
        side="SKINSCAB",
        floor="FLOOR6_2",
        ceiling="FLAT18",
        door="DOORRED",
        accent=(235, 120, 40),
        grade=(1.2, 0.9, 0.8),
        blood=True,
        props=[("POL3B0", 0.13, 0.95, 4.6), ("POL3A0", 0.87, 0.96, 4.6)],
    ),
    "throne": dict(
        label="Тронный зал",
        wall="GSTONE2",
        side="SKINMET1",
        floor="FLAT20",
        ceiling="FLAT23",
        door="BIGDOOR3",
        accent=(255, 80, 40),
        grade=(1.18, 0.9, 0.86),
        blood=True,
        back=(0.14, 0.08, 0.86, 0.79),
        props=[("POL3A0", 0.1, 0.96, 5.0), ("POL3B0", 0.9, 0.97, 5.0)],
    ),
    "void": dict(
        label="Пустота",
        wall="BLODRIP1",
        side="SKIN2",
        floor="FLOOR7_1",
        ceiling="FLAT2",
        door="DOORRED2",
        accent=(180, 20, 20),
        grade=(1.2, 0.82, 0.82),
        blood=True,
        portal="none",
        fog=0.10,
        props=[("POL5A0", 0.18, 0.97, 3.4), ("POL5A0", 0.82, 0.98, 3.0)],
    ),
    "vault": dict(
        label="Хранилище",
        wall="METAL2",
        side="METAL5",
        floor="FLOOR0_3",
        ceiling="CEIL4_3",
        door="BIGDOOR1",
        accent=(180, 200, 120),
        props=[("BAR1A0", 0.13, 0.95, 3.6), ("BAR1B0", 0.87, 0.97, 3.8)],
    ),
}

SOUNDS = {
    "click": ["DSPISTOL", "DSPSTOL"],
    "shotgun": ["DSSHOTGN", "DSSHOTG"],
    "squish": ["DSSLOP", "DSGIB"],
    "door": ["DSDOROPN", "DSBDOPN"],
    "boom": ["DSBAREXP", "DSEXPLOD"],
    "pain": ["DSPODTH1", "DSOOF"],
    "player_pain": ["DSPLPAIN", "DSOOF"],
    "item": ["DSITEMUP", "DSGETPOW"],
    "weapon_up": ["DSWPNUP"],
    "switch": ["DSSWTCHN", "DSSWTCHX"],
    "secret": ["DSMANSIT", "DSSECRET"],
    "teleport": ["DSTELEPT", "DSTELEP"],
    "fire": ["DSFLAME", "DSFIRE"],
    "skeleton": ["DSSKESIT", "DSPOSIT1"],
}

MUSIC = {
    "title": ["D_DM2TTL", "D_INTRO", "D_DM2INT"],
    "map": ["D_RUNNIN", "D_E1M1"],
    "office": ["D_SHAWN", "D_E1M2"],
    "chase": ["D_DOOM", "D_E1M8"],
    "hell": ["D_THE_DA", "D_E3M1"],
    "boss": ["D_OPENIN", "D_E3M8"],
    "ending": ["D_READ_M", "D_VICTOR"],
    "menu": ["D_DM2INT", "D_INTER"],
}


# --------------------------------------------------------------------- helpers


def pick(wad: Wad, names: list[str]) -> str | None:
    for name in names:
        if name in wad:
            return name
    return None


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# Files in game/gui that come from the Ren'Py template rather than the IWAD.
# Everything else under game/gui is generated and may be pruned.
GUI_KEEP = {"bubble.png", "thoughtbubble.png"}
GUI_GENERATED_DIRS = ("button", "choice", "bar", "slider", "scrollbar", "overlay")


def prune_generated(game: Path, keep_music: bool) -> None:
    """Delete output from a previous build so the tree matches the manifest.

    Without this, rebuilding from a different IWAD over an existing checkout
    leaves stale files behind and `verify_assets.py` (rightly) complains that
    the manifest and the disk disagree.  A build should be reproducible, so
    anything this script owns gets removed first.

    `keep_music` preserves game/audio/music when --skip-music was passed, so a
    quick UI-only rebuild does not throw away a rendered soundtrack.
    """
    for name in ("images", "fonts"):
        target = game / name
        if target.is_dir():
            shutil.rmtree(target)

    sfx = game / "audio" / "sfx"
    if sfx.is_dir():
        shutil.rmtree(sfx)
    if not keep_music:
        music = game / "audio" / "music"
        if music.is_dir():
            shutil.rmtree(music)

    gui = game / "gui"
    if gui.is_dir():
        for sub in GUI_GENERATED_DIRS:
            target = gui / sub
            if target.is_dir():
                shutil.rmtree(target)
        for item in gui.iterdir():
            if item.is_file() and item.name not in GUI_KEEP:
                item.unlink()


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


# Candidates for a TTF with Cyrillic coverage, in priority order.  The copy
# bundled with the repo wins: the Cyrillic bitmap fonts must be identical no
# matter who runs the build or which platform they are on, otherwise every
# rebuild would rewrite game/fonts with a different typeface.
BUNDLED_TTF = Path(__file__).resolve().parent / "fonts" / "DejaVuSans.ttf"

TTF_CANDIDATES = [
    "renpy/common/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/Library/Fonts/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "C:/Windows/Fonts/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
]


def find_cyrillic_ttf(explicit: str | None = None) -> Path | None:
    """Locate a TrueType font that can render Russian.

    Search order: the --ttf argument, the DOOM_NOVELL_TTF environment variable,
    the DejaVu Sans bundled in tools/fonts (this is the normal path), a DejaVu
    next to the Ren'Py SDK (RENPY_SDK / RENPY_SH), then the usual per-platform
    font directories as a last resort.
    """
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists():
            return path
        print(f"    ! --ttf {explicit} does not exist, falling back to discovery", file=sys.stderr)

    from_env = os.environ.get("DOOM_NOVELL_TTF")
    if from_env:
        path = Path(from_env).expanduser()
        if path.exists():
            return path
        print(f"    ! DOOM_NOVELL_TTF={from_env} does not exist, ignoring", file=sys.stderr)

    if BUNDLED_TTF.exists():
        return BUNDLED_TTF

    # A Ren'Py SDK almost certainly contains DejaVuSans.ttf.
    sdk_roots = []
    for var in ("RENPY_SDK", "RENPY_BASE"):
        value = os.environ.get(var)
        if value:
            sdk_roots.append(Path(value))
    renpy_sh = os.environ.get("RENPY_SH")
    if renpy_sh:
        sdk_roots.append(Path(renpy_sh).resolve().parent)
    for root in sdk_roots:
        candidate = root / "renpy" / "common" / "DejaVuSans.ttf"
        if candidate.exists():
            return candidate

    for name in TTF_CANDIDATES:
        path = Path(name)
        if path.exists():
            return path

    return None


def to_ogg(wav_bytes: bytes, out_path: Path) -> bool:
    tmp = out_path.with_suffix(".tmp.wav")
    tmp.write_bytes(wav_bytes)
    try:
        # `+bitexact` strips encoder version strings and timestamps from the
        # container, so re-rendering the same score produces the same bytes
        # instead of churning the repository on every rebuild.
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-fflags", "+bitexact",
                "-i", str(tmp),
                "-c:a", "libvorbis", "-q:a", "4",
                "-flags:a", "+bitexact",
                "-map_metadata", "-1",
                str(out_path),
            ],
            capture_output=True,
        )
        return result.returncode == 0 and out_path.exists()
    finally:
        tmp.unlink(missing_ok=True)


def sprite_frames(wad: Wad, prefix: str) -> dict[str, str]:
    """Map rotation-1 frame letters to lump names for a sprite prefix."""
    frames: dict[str, str] = {}
    for lump in wad.sprite_names:
        if not lump.startswith(prefix) or len(lump) < 6:
            continue
        letter = lump[4]
        rotation = lump[5]
        if rotation in ("1", "0") and letter not in frames:
            frames[letter] = lump
    return frames


def framed_sprite(wad: Wad, prefix: str, mood: str, height: int) -> Image.Image | None:
    frames = sprite_frames(wad, prefix)
    for letter_frame in MOODS[mood]:
        lump = frames.get(letter_frame[0])
        if lump is None:
            continue
        sprite = wad.sprite(lump)
        factor = height / sprite.height
        return sprite_on_stage(wad, lump, factor, shadow=(mood != "dead"))
    return None


# ----------------------------------------------------------------- main build


def pcm_hash(pcm16: np.ndarray) -> str:
    """Stable fingerprint of the rendered audio (not of the encoded file)."""
    return hashlib.sha256(pcm16.tobytes()).hexdigest()


def build_music(wad: Wad, music_dir: Path, manifest: dict, previous: dict | None = None) -> None:
    """Render every MUS/MIDI track in MUSIC into OGG (or WAV) files.

    Re-encoding is skipped when the rendered audio is bit-identical to the
    previous build (``previous`` is the old wad_manifest.json).  libvorbis
    output is not reproducible, so without this every rebuild would rewrite
    eight tracks and churn the repository.
    """
    use_ogg = ffmpeg_available()

    ## Accept either a full manifest ({"audio": {...}}) or the audio mapping
    ## itself, so callers cannot get this wrong.
    previous = previous or {}
    if "audio" in previous and isinstance(previous["audio"], dict):
        previous = previous["audio"]
    for key, names in MUSIC.items():
        lump = pick(wad, names)
        if lump is None:
            print(f"    ! music {key}: none of {names} present")
            continue
        data = wad.bytes(lump)
        try:
            if data.startswith(b"MUS\x1a"):
                song = wad_audio.parse_mus(data)
            else:
                from wadlib.audio import parse_midi

                song = parse_midi(data)
            if len(song) < 4:
                print(f"    ! music {key}: {lump} parsed to {len(song)} notes, skipped")
                continue
            started = time.time()
            stereo = wad_audio.render_mus(song)
            wav = wad_audio.stereo_to_wav(stereo)
        except Exception as exc:  # noqa: BLE001
            print(f"    ! music {key} ({lump}): {exc}")
            continue

        ogg_path = music_dir / f"{key}.ogg"
        wav_path = music_dir / f"{key}.wav"

        pcm = np.clip(stereo, -1.0, 1.0)
        pcm16 = (pcm * 32767).astype("<i2").reshape(-1)
        digest = pcm_hash(pcm16)

        old = previous.get(f"music_{key}") or {}
        reusable = (
            old.get("pcm_sha256") == digest
            and old.get("lump") == lump
            and (music_dir / str(old.get("file", ""))).exists()
        )

        if reusable:
            target = music_dir / old["file"]
            note = "unchanged"
        elif use_ogg and to_ogg(wav, ogg_path):
            target = ogg_path
            note = "encoded"
        else:
            wav_path.write_bytes(wav)
            target = wav_path
            note = "wav"

        manifest["audio"][f"music_{key}"] = {
            "lump": lump,
            "file": target.name,
            "notes": len(song),
            "seconds": round(len(stereo) / wad_audio.SAMPLE_RATE, 1),
            "pcm_sha256": digest,
        }
        print(
            f"    {key:8s} {lump:10s} {len(song):5d} notes "
            f"{len(stereo) / wad_audio.SAMPLE_RATE:6.1f}s  "
            f"({time.time() - started:.1f}s render, {note})"
        )


def build(args: argparse.Namespace) -> int:
    started = time.time()
    iwad_path = Path(args.iwad).expanduser().resolve()
    if not iwad_path.exists():
        print(f"! IWAD not found: {iwad_path}", file=sys.stderr)
        return 2

    wad = Wad(iwad_path)
    root = Path(args.out).expanduser().resolve()
    game = root / "game"

    print(f"[0/6] clearing output from a previous build")
    prune_generated(game, keep_music=args.skip_music)

    ## Read the manifest before it is overwritten: build_music uses it to tell
    ## which tracks are already rendered and can be left alone.
    previous_manifest: dict = {}
    old_manifest_path = game / "wad_manifest.json"
    if old_manifest_path.exists():
        try:
            previous_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
        except Exception:
            previous_manifest = {}

    images = {name: ensure_dir(game / "images" / name) for name in ("bg", "chars", "items", "maps", "ui", "fx")}
    gui = ensure_dir(game / "gui")
    for sub in ("button", "choice", "bar", "slider", "scrollbar", "overlay"):
        ensure_dir(gui / sub)
    sfx_dir = ensure_dir(game / "audio" / "sfx")
    music_dir = ensure_dir(game / "audio" / "music")
    fonts_dir = ensure_dir(game / "fonts")

    print(wad.banner())
    manifest: dict = {
        "tool_version": TOOL_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "iwad": {
            "file": iwad_path.name,
            "magic": wad.magic,
            "lumps": wad.numlumps,
            "sha256": hashlib.sha256(iwad_path.read_bytes()).hexdigest(),
        },
        "art": {},
        "audio": {},
        "fonts": {},
        "maps": [],
    }

    # ---------------------------------------------------------------- sprites
    print("[1/6] characters and items")
    for key, spec in CHARACTERS.items():
        got = 0
        for mood in MOODS:
            img = framed_sprite(wad, spec["sprite"], mood, spec["height"])
            if img is None:
                continue
            write_png(img, images["chars"] / f"{key}_{mood}.png")
            got += 1
        manifest["art"][f"char_{key}"] = {"sprite": spec["sprite"], "moods": got}
        if not got:
            print(f"    ! {key}: sprite {spec['sprite']} not found in this IWAD")

    for key, lump in ITEM_SPRITES.items():
        if lump not in wad:
            print(f"    ! item {key}: {lump} missing")
            continue
        sprite = wad.sprite(lump)
        factor = max(1, int(64 / sprite.height)) if sprite.height < 64 else 1
        write_png(scale_nearest(sprite, factor), images["items"] / f"{key}.png")
    for key, lump in PROP_SPRITES.items():
        if lump in wad:
            write_png(scale_nearest(wad.sprite(lump), 2), images["ui"] / f"prop_{key}.png")

    # ----------------------------------------------------------------- scenes
    print("[2/6] backgrounds")
    for key, spec in SCENES.items():
        try:
            scene_spec = SceneSpec(
                key=key,
                wall=spec["wall"],
                side=spec["side"],
                floor=spec["floor"],
                ceiling=spec["ceiling"],
                accent=spec["accent"],
                door=spec.get("door", "wall"),
                portal=spec.get("portal", "door"),
                back=spec.get("back", (0.20, 0.12, 0.80, 0.76)),
                blood=spec.get("blood", False),
                grade=spec.get("grade", (1.0, 1.0, 1.0)),
                fog=spec.get("fog", 0.05),
                props=spec.get("props", []),
                seed=len(key) * 7 + 3,
            )
            img = compose_scene(wad, scene_spec)
        except WadError as exc:
            print(f"    ! scene {key}: {exc}")
            continue
        write_png(img, images["bg"] / f"{key}.png")
        manifest["art"][f"bg_{key}"] = {
            "wall": spec["wall"],
            "floor": spec["floor"],
            "door": spec.get("door"),
        }

    # -------------------------------------------------------------- floorplans
    print("[3/6] level archives")
    map_names = [n for n in wad.names if n.startswith("MAP") and n[3:].isdigit()]
    if not map_names:
        map_names = [n for n in wad.names if len(n) == 4 and n[0] == "E" and n[2] == "M" and n[1].isdigit()]
    monster_sprites: dict[int, Image.Image] = {}
    for ttype, (prefix, _rot, _label, _is_monster) in THING_TYPES.items():
        frames = sprite_frames(wad, prefix)
        if frames:
            monster_sprites[ttype] = wad.sprite(frames.get("A", next(iter(frames.values()))))

    for mapname in sorted(map_names):
        try:
            level = Level.load(wad, mapname)
        except Exception as exc:  # noqa: BLE001 - skip malformed maps
            print(f"    ! map {mapname}: {exc}")
            continue
        plan = render_floorplan(wad, level, (512, 320), monster_sprites=monster_sprites)
        write_png(plan, images["maps"] / f"{mapname.lower()}.png")
        manifest["maps"].append({"name": mapname, "sectors": len(level.sectors), "things": len(level.things)})

    if manifest["maps"]:
        hero = Level.load(wad, manifest["maps"][0]["name"])
        hero_img = render_floorplan(wad, hero, (1280, 720), margin=40, monster_sprites=monster_sprites, sprite_scale=0.5)
        hero_img = add_grain(hero_img, 4, 5)
        write_png(hero_img, images["ui"] / "map_hero.png")

    # -------------------------------------------------------------------- UI
    print("[4/6] interface chrome")
    CHROME = "BROWN1"
    METAL = "METAL1"
    write_png(plate(wad, CHROME, (1280, 185), brightness=0.34, shade=0.8), gui / "textbox.png")
    write_png(plate(wad, METAL, (512, 58), brightness=0.42, rivets=False), gui / "namebox.png")
    write_png(plate(wad, CHROME, (128, 128), brightness=0.4), gui / "frame.png")
    write_png(plate(wad, CHROME, (640, 400), brightness=0.4, rivets=True), gui / "confirm_frame.png")
    write_png(plate(wad, METAL, (640, 56), brightness=0.36, rivets=False), gui / "skip.png")
    write_png(plate(wad, METAL, (560, 56), brightness=0.40, rivets=False), gui / "notify.png")
    write_png(plate(wad, CHROME, (1280, 640), brightness=0.30, shade=0.6), gui / "nvl.png")

    write_png(plate(wad, METAL, (300, 34), brightness=0.42, rivets=False, seed=5), gui / "button" / "idle_background.png")
    write_png(plate(wad, METAL, (300, 34), brightness=0.66, rivets=False, seed=6, red=True), gui / "button" / "hover_background.png")
    write_png(plate(wad, METAL, (300, 34), brightness=0.55, rivets=False, seed=7), gui / "button" / "selected_idle_background.png")
    write_png(plate(wad, METAL, (300, 34), brightness=0.75, rivets=False, seed=8, red=True), gui / "button" / "selected_hover_background.png")
    write_png(plate(wad, METAL, (300, 34), brightness=0.24, rivets=False, seed=9), gui / "button" / "insensitive_background.png")
    write_png(plate(wad, METAL, (276, 206), brightness=0.34, seed=10), gui / "button" / "slot_idle_background.png")
    write_png(plate(wad, METAL, (276, 206), brightness=0.5, seed=11, red=True), gui / "button" / "slot_hover_background.png")

    write_png(plate(wad, METAL, (790, 66), brightness=0.34, seed=12, rivets=False), gui / "choice" / "idle_background.png")
    write_png(plate(wad, METAL, (790, 66), brightness=0.58, seed=13, rivets=False, red=True), gui / "choice" / "hover_background.png")

    # Bars, sliders, scrollbars: flat strips with a bevel, sized like the GUI wants.
    write_png(plate(wad, METAL, (350, 25), brightness=0.5, rivets=False, seed=20), gui / "bar" / "left.png")
    write_png(plate(wad, METAL, (350, 25), brightness=0.22, rivets=False, seed=21), gui / "bar" / "right.png")
    write_png(plate(wad, METAL, (25, 350), brightness=0.5, rivets=False, seed=22), gui / "bar" / "top.png")
    write_png(plate(wad, METAL, (25, 350), brightness=0.22, rivets=False, seed=23), gui / "bar" / "bottom.png")

    for state, bright in (("idle", 0.26), ("hover", 0.44)):
        write_png(plate(wad, METAL, (350, 25), brightness=bright, rivets=False, seed=30), gui / "slider" / f"horizontal_{state}_bar.png")
        write_png(plate(wad, METAL, (10, 25), brightness=bright + 0.3, rivets=False, seed=31), gui / "slider" / f"horizontal_{state}_thumb.png")
        write_png(plate(wad, METAL, (25, 350), brightness=bright, rivets=False, seed=32), gui / "slider" / f"vertical_{state}_bar.png")
        write_png(plate(wad, METAL, (25, 10), brightness=bright + 0.3, rivets=False, seed=33), gui / "slider" / f"vertical_{state}_thumb.png")
        write_png(plate(wad, METAL, (700, 12), brightness=bright, rivets=False, seed=34), gui / "scrollbar" / f"horizontal_{state}_bar.png")
        write_png(plate(wad, METAL, (700, 12), brightness=bright + 0.3, rivets=False, seed=35), gui / "scrollbar" / f"horizontal_{state}_thumb.png")
        write_png(plate(wad, METAL, (12, 700), brightness=bright, rivets=False, seed=36), gui / "scrollbar" / f"vertical_{state}_bar.png")
        write_png(plate(wad, METAL, (12, 700), brightness=bright + 0.3, rivets=False, seed=37), gui / "scrollbar" / f"vertical_{state}_thumb.png")

    # Check / radio markers: transparent backgrounds with a bright tick.
    for kind, size in (("check", (18, 34)), ("radio", (18, 34))):
        base = Image.new("RGBA", size, (0, 0, 0, 0))
        write_png(base, gui / "button" / f"{kind}_foreground.png")
        mark = base.copy()
        draw = ImageDraw.Draw(mark)
        draw.rectangle([4, 11, 12, 22], fill=(226, 74, 40, 235), outline=(255, 220, 190, 200))
        write_png(mark, gui / "button" / f"{kind}_selected_foreground.png")

    # Overlays.
    main_overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    arr = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(arr)
    draw.rectangle([0, 0, 1280, 720], fill=(0, 0, 0, 90))
    write_png(arr, gui / "overlay" / "main_menu.png")
    write_png(arr, gui / "overlay" / "game_menu.png")
    confirm = Image.new("RGBA", (1280, 720), (0, 0, 0, 170))
    write_png(confirm, gui / "overlay" / "confirm.png")
    del main_overlay, draw

    # Menu backgrounds.
    write_png(title_screen(wad), gui / "main_menu.png")
    menu_scene = compose_scene(
        wad,
        SceneSpec(
            key="menu",
            wall=SCENES["corridor"]["wall"],
            side=SCENES["corridor"]["side"],
            floor=SCENES["corridor"]["floor"],
            ceiling=SCENES["corridor"]["ceiling"],
            door=SCENES["corridor"]["door"],
            accent=(150, 40, 30),
            props=[("POL5A0", 0.2, 0.98, 3.0)],
            seed=77,
        ),
    )
    write_png(menu_scene, gui / "game_menu.png")

    # Custom sprites for the game itself.
    write_png(logo(wad, "M_DOOM", 150), images["ui"] / "logo.png")
    write_png(scanlines((1280, 720), 3, 34), images["ui"] / "scanlines.png")
    write_png(vignette((1280, 720), 0.85, 2.2), images["ui"] / "vignette.png")

    # Crosshair cursor, built from WAD patch pixels.
    cursor = Image.new("RGBA", (38, 38), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cursor)
    cd.arc([4, 4, 33, 33], 0, 360, fill=(232, 60, 34, 220), width=2)
    cd.line([18, 0, 18, 11], fill=(232, 60, 34, 220), width=2)
    cd.line([18, 26, 18, 37], fill=(232, 60, 34, 220), width=2)
    cd.line([0, 18, 11, 18], fill=(232, 60, 34, 220), width=2)
    cd.line([26, 18, 37, 18], fill=(232, 60, 34, 220), width=2)
    cd.point((18, 18), fill=(255, 230, 200, 240))
    write_png(cursor, images["ui"] / "cursor.png")

    # ------------------------------------------------------------------ fonts
    print("[5/6] fonts")
    font_specs: list[tuple[str, Path, int]] = []
    for key, scale in (("doom1", 2), ("doom2", 3), ("doom3", 4)):
        patch_font(wad, fonts_dir / f"{key}.fnt", fonts_dir / f"{key}_0.png", scale=scale, name=key)
        font_specs.append((key, fonts_dir / f"{key}.fnt", scale * 7))

    ttf = find_cyrillic_ttf(args.ttf)
    if ttf is None:
        print(
            "    ! no TTF with Cyrillic found. The game is in Russian, so this is fatal.\n"
            "      Pass --ttf PATH, or set DOOM_NOVELL_TTF, or install a DejaVu font:\n"
            "        Debian/Ubuntu: sudo apt-get install fonts-dejavu-core\n"
            "        macOS:         brew install --cask font-dejavu",
            file=sys.stderr,
        )
        return 3

    print(f"    cyrillic source: {ttf}")
    for size in (20, 26, 32, 44):
        key = f"cyr{size}"
        ttf_font(ttf, fonts_dir / f"{key}.fnt", fonts_dir / f"{key}_0.png", size=size, name=key)
        font_specs.append((key, fonts_dir / f"{key}.fnt", size))
    manifest["fonts"]["ttf_source"] = str(ttf)

    font_table = {}
    for key, fnt_path, size in font_specs:
        metrics = read_metrics(fnt_path)
        font_table[key] = {
            "file": f"fonts/{fnt_path.name}",
            "size": size,
            "line_height": metrics["line_height"],
            "base": metrics["base"],
        }
    (fonts_dir / "fonts.json").write_text(json.dumps(font_table, indent=2), encoding="utf-8")
    manifest["fonts"].update(font_table)

    # ------------------------------------------------------------------ audio
    print("[6/6] audio")
    for key, names in SOUNDS.items():
        lump = pick(wad, names)
        if lump is None:
            print(f"    ! sfx {key}: none of {names} present")
            continue
        try:
            wav = wad_audio.dmx_to_wav(wad.bytes(lump))
        except Exception as exc:  # noqa: BLE001
            print(f"    ! sfx {key}: {exc}")
            continue
        (sfx_dir / f"{key}.wav").write_bytes(wav)
        manifest["audio"][f"sfx_{key}"] = lump

    if not args.skip_music:
        build_music(wad, music_dir, manifest, previous_manifest)

    # ------------------------------------------------------------------- icon
    print("[icon] application icon")
    icon_size = 256
    icon = Image.new("RGBA", (icon_size, icon_size), (8, 6, 6, 255))
    try:
        backdrop = scale_nearest(wad.texture("MARBLE1"), 2).resize((icon_size, icon_size), Image.NEAREST)
        icon.alpha_composite(backdrop)
    except Exception:  # noqa: BLE001
        pass
    icon = Image.blend(icon, Image.new("RGBA", icon.size, (120, 20, 12, 255)), 0.22)
    for lump, box_h, y_at in (("HEADB1", 132, 118),):
        if lump not in wad:
            continue
        sprite = wad.sprite(lump)
        sprite = scale_nearest(sprite, box_h / sprite.height)
        icon.alpha_composite(sprite, ((icon_size - sprite.width) // 2, y_at))
    try:
        log = logo(wad, "M_DOOM", 74)
        icon.alpha_composite(log, ((icon_size - log.width) // 2, 18))
    except WadError:
        pass
    save_ico(icon, root / "icon.ico")
    write_png(icon, root / "icon.png")
    write_png(icon, game / "gui" / "window_icon.png")
    manifest["art"]["icon"] = "icon.ico"

    # -------------------------------------------------------------- manifest
    ## Music may be kept from a previous build (--skip-music), in which case the
    ## manifest should describe what is actually on disk rather than what this
    ## run rendered.  verify_assets.py compares the two, so they must agree.
    music_on_disk = len(list(music_dir.glob("*.*"))) if music_dir.is_dir() else 0

    manifest["counts"] = {
        "characters": len(CHARACTERS),
        "scenes": len([k for k in manifest["art"] if k.startswith("bg_")]),
        "maps": len(manifest["maps"]),
        "sounds": len([k for k in manifest["audio"] if k.startswith("sfx_")]),
        "music": music_on_disk,
    }
    manifest["elapsed_seconds"] = round(time.time() - started, 1)
    (game / "wad_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\ndone in {manifest['elapsed_seconds']}s")
    for key, value in manifest["counts"].items():
        print(f"  {key:12s} {value}")
    print(f"  manifest     {game / 'wad_manifest.json'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build DOOM_Novell assets from an IWAD.")
    ap.add_argument("--iwad", default="doom2.wad", help="path to DOOM2.WAD / FREEDOOM2.WAD / doom.wad")
    ap.add_argument("--out", default=".", help="project root (the folder that contains game/)")
    ap.add_argument("--ttf", default=None, help="TTF used for Cyrillic glyphs")
    ap.add_argument("--skip-music", action="store_true", help="skip the (slow) music rendering")
    ap.add_argument("--music-only", action="store_true", help="only re-render the soundtrack")
    args = ap.parse_args(argv)

    if args.music_only:
        iwad_path = Path(args.iwad).expanduser().resolve()
        wad = Wad(iwad_path)
        game_dir = Path(args.out).expanduser().resolve() / "game"
        music_dir = ensure_dir(game_dir / "audio" / "music")

        ## Reuse the existing manifest so unchanged tracks are not re-encoded.
        manifest_path = game_dir / "wad_manifest.json"
        previous: dict = {}
        if manifest_path.exists():
            try:
                previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}

        manifest: dict = {"audio": {}}
        print(wad.banner())
        build_music(wad, music_dir, manifest, previous)

        ## Merge the refreshed audio entries back into the manifest.
        if manifest_path.exists():
            merged = json.loads(manifest_path.read_text(encoding="utf-8"))
            merged.setdefault("audio", {}).update(manifest["audio"])
            merged.setdefault("counts", {})["music"] = len(list(music_dir.glob("*.*")))
            manifest_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  updated  {manifest_path}")
        return 0

    return build(args)


if __name__ == "__main__":
    raise SystemExit(main())