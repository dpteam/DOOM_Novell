"""Throwaway preview renderer used while tuning the art pipeline.

    python tools/preview.py <iwad> <outdir>

Writes a handful of PNGs so a human (or an agent with eyes) can check the
look before the whole game is built.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wadlib.art import SceneSpec, compose_scene, plate, title_screen, logo
from wadlib.wadfile import Wad

OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "preview")
WAD = Path(sys.argv[1] if len(sys.argv) > 1 else "doom2.wad")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wad = Wad(WAD)

    tech = SceneSpec(
        key="tech",
        wall="STARTAN3",
        side="SUPPORT2",
        floor="FLOOR4_8",
        ceiling="CEIL3_5",
        accent=(70, 150, 190),
        props=[("COLUA0", 0.13, 0.93, 2.4), ("BAR1A0", 0.87, 0.95, 2.0)],
        seed=4,
    )
    hell = SceneSpec(
        key="hell",
        wall="MARBLE1",
        side="SKIN2",
        floor="FLOOR7_2",
        ceiling="FLAT1",
        accent=(190, 60, 30),
        blood=True,
        props=[("POL3A0", 0.16, 0.94, 2.2), ("POL3B0", 0.84, 0.96, 2.0)],
        grade=(1.12, 0.94, 0.86),
        seed=9,
    )
    compose_scene(wad, tech).save(OUT / "scene_tech.png")
    compose_scene(wad, hell).save(OUT / "scene_hell.png")
    title_screen(wad).save(OUT / "title.png")
    plate(wad, "BROWN1", (1280, 185)).save(OUT / "textbox.png")
    plate(wad, "STARTAN3", (790, 64), brightness=0.7).save(OUT / "choice_idle.png")
    logo(wad, "M_DOOM", 180).save(OUT / "logo.png")
    wad.patch("TITLEPIC").save(OUT / "titlepic_raw.png")
    wad.patch("STCFN065").resize((24, 48)).save(OUT / "glyph_a.png")
    print("wrote", OUT.resolve())


if __name__ == "__main__":
    main()