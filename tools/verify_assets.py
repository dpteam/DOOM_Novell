"""Consistency checks for the generated game data.

This is the cheap gate that runs in CI on every push.  It does not need an
IWAD, an SDK or a GPU - it just compares the committed files against each
other and against the generated manifests, and it catches the mistakes that
actually happened while building this project:

* a font registered at a size that does not match its .fnt
* a ``{size=N}`` tag pointing at a bitmap font size that does not exist
* an image declared in images.rpy but missing on disk (or vice versa)
* a .fnt whose atlas page is not next to it
* audio referenced by the manifest but not present

    python tools/verify_assets.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "game"

problems: list[str] = []
notes: list[str] = []


def fail(message: str) -> None:
    problems.append(message)


def ok(message: str) -> None:
    notes.append(message)


# ------------------------------------------------------------------ fonts.json


def check_fonts() -> None:
    fonts_json = GAME / "fonts" / "fonts.json"
    if not fonts_json.exists():
        fail("game/fonts/fonts.json is missing - run tools/build_assets.py")
        return

    table = json.loads(fonts_json.read_text(encoding="utf-8"))
    if not table:
        fail("fonts.json is empty")
        return

    for name, info in table.items():
        fnt = GAME / info["file"]
        if not fnt.exists():
            fail(f"fonts.json lists {info['file']} for {name}, but the file is missing")
            continue

        text = fnt.read_text(encoding="utf-8")

        # The declared size must match what the .fnt says about its own metrics.
        common = re.search(r"common .*lineHeight=(\d+) base=(\d+)", text)
        if not common:
            fail(f"{info['file']}: no 'common' line")
            continue
        line_height, base = int(common.group(1)), int(common.group(2))
        if info.get("line_height") and info["line_height"] != line_height:
            fail(
                f"{info['file']}: fonts.json says line_height={info['line_height']}, "
                f"the .fnt says {line_height}"
            )
        if info.get("base") and info["base"] != base:
            fail(f"{info['file']}: fonts.json says base={info['base']}, the .fnt says {base}")

        # The atlas page must exist; Ren'Py resolves it relative to game/.
        page = re.search(r'page id=0 file="([^"]+)"', text)
        if not page:
            fail(f"{info['file']}: no page line")
            continue
        page_path = GAME / page.group(1)
        if not page_path.exists():
            fail(f"{info['file']}: atlas page {page.group(1)} does not exist")

        # Every registered size must be drawable: a bitmap font has exactly one.
        chars = re.findall(r"^char id=(\d+) ", text, re.MULTILINE)
        if not chars:
            fail(f"{info['file']}: no glyphs")
        elif len(chars) < 32:
            fail(f"{info['file']}: only {len(chars)} glyphs, expected a full alphabet")

    ok(f"fonts: {len(table)} registered")


# ------------------------------------------------------------------- images.rpy


def check_images() -> None:
    images_rpy = GAME / "images.rpy"
    if not images_rpy.exists():
        fail("game/images.rpy is missing - run tools/gen_images_rpy.py")
        return

    text = images_rpy.read_text(encoding="utf-8")
    declared = set(re.findall(r'image [^=]+= "([^"]+)"', text))

    missing = sorted(p for p in declared if not (GAME / p).exists())
    for path in missing:
        fail(f"images.rpy declares {path}, but the file does not exist")

    on_disk = {
        str(p.relative_to(GAME)).replace("\\", "/")
        for sub in ("images/bg", "images/chars", "images/items", "images/maps", "images/ui")
        for p in (GAME / sub).glob("*.png")
    }
    undeclared = sorted(on_disk - declared)
    if undeclared:
        fail(
            "images exist but are not declared in images.rpy "
            f"(run tools/gen_images_rpy.py): {', '.join(undeclared[:5])}"
            + (" ..." if len(undeclared) > 5 else "")
        )

    ok(f"images: {len(declared)} declared, all present")


# ------------------------------------------------------------------------ fonts


FONT_REF = re.compile(r'font\s+"([^"]+)"')
SIZE_REF = re.compile(r"^\s*size\s+(\d+)\s*$")


def check_style_fonts() -> None:
    table = json.loads((GAME / "fonts" / "fonts.json").read_text(encoding="utf-8"))
    registered = {info["file"]: info["size"] for info in table.values()}

    for path in sorted(GAME.rglob("*.rpy")):
        if path.name.startswith("_"):
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            match = FONT_REF.search(line)
            if not match:
                continue
            font = match.group(1)
            if not font.startswith("fonts/"):
                continue
            if font not in registered:
                fail(f"{path.name}:{i + 1}: font {font} is not in fonts.json")
                continue

            # Look ahead for the size that applies to this block.
            for follow in lines[i + 1 : i + 8]:
                size_match = SIZE_REF.match(follow)
                if size_match:
                    size = int(size_match.group(1))
                    if size != registered[font]:
                        fail(
                            f"{path.name}:{i + 1}: font {font} is registered at "
                            f"{registered[font]}px but the style asks for {size}px"
                        )
                    break
                if follow and not follow.startswith((" ", "\t")):
                    break

    ok("style fonts: all references resolve to a registered size")


def check_no_size_tags() -> None:
    """`{size=N}` cannot work with a bitmap font, and Ren'Py 8.5 hard-crashes."""
    pattern = re.compile(r"\{size=")
    for path in sorted(GAME.rglob("*.rpy")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                fail(
                    f"{path.name}:{i + 1}: '{{size=...}}' tag - bitmap fonts only have one "
                    f"size; use a style with its own .fnt instead"
                )
    ok("text: no {size=} tags")


# ------------------------------------------------------------------------ audio


def check_audio() -> None:
    manifest_path = GAME / "wad_manifest.json"
    if not manifest_path.exists():
        fail("game/wad_manifest.json is missing")
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for key, value in manifest.get("audio", {}).items():
        if key.startswith("sfx_"):
            path = GAME / "audio" / "sfx" / f"{key[4:]}.wav"
            if not path.exists():
                fail(f"manifest lists {key}, but {path.relative_to(GAME)} is missing")
        elif key.startswith("music_"):
            name = value["file"]
            path = GAME / "audio" / "music" / name
            if not path.exists():
                fail(f"manifest lists {key} as {name}, but it is missing")

    sfx = len(list((GAME / "audio" / "sfx").glob("*.wav")))
    music = len(list((GAME / "audio" / "music").glob("*.*")))
    ok(f"audio: {sfx} sound effects, {music} music tracks")


def check_manifest_counts() -> None:
    manifest = json.loads((GAME / "wad_manifest.json").read_text(encoding="utf-8"))
    counts = manifest.get("counts", {})

    actual = {
        "scenes": len(list((GAME / "images" / "bg").glob("*.png"))),
        "maps": len(list((GAME / "images" / "maps").glob("*.png"))),
        "sounds": len(list((GAME / "audio" / "sfx").glob("*.wav"))),
        "music": len(list((GAME / "audio" / "music").glob("*.*"))),
    }
    for key, value in actual.items():
        declared = counts.get(key)
        if declared is not None and declared != value:
            fail(f"manifest counts.{key}={declared}, but {value} files are present")

    ok("manifest: counts match the files on disk")


def main() -> int:
    print(f"verifying {GAME}")
    check_fonts()
    check_images()
    check_style_fonts()
    check_no_size_tags()
    check_audio()
    check_manifest_counts()

    print()
    for note in notes:
        print(f"  ok   {note}")

    if problems:
        print()
        for problem in problems:
            print(f"  FAIL {problem}")
        print(f"\n{len(problems)} problem(s) found")
        return 1

    print("\nassets are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())