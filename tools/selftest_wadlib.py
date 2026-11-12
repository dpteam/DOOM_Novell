"""Self-test for `tools/wadlib`, using a synthetic WAD built in memory.

DOOM2.WAD is proprietary and must never end up in CI, so this script builds a
tiny WAD from scratch and checks that the decoders return the values they were
given.  It covers exactly the formats that were painful to get right:

* PLAYPAL / COLORMAP palette translation
* the column/post PATCH format used by every sprite and wall patch
* 64x64 flats
* DMX sound lumps (unsigned 8-bit with 16-byte padding on both ends)
* MUS music, including the "last event carries the delta" quirk

Run it with plain Python - no Pillow or numpy needed for the WAD part, though
the audio checks do use numpy.

    python tools/selftest_wadlib.py
"""

from __future__ import annotations

import io
import struct
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from wadlib.audio import dmx_to_wav, parse_mus
from wadlib.wadfile import Wad

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILURES.append(name)


def check_equal(name: str, got, want) -> None:
    check(name, got == want, f"(got {got!r}, want {want!r})")


# --------------------------------------------------------------------- builders


def build_palette() -> bytes:
    """Palette 0: entry i is (i, 0, 255-i). The other 13 are black."""
    pal = bytearray(768 * 14)
    for i in range(256):
        pal[i * 3] = i
        pal[i * 3 + 1] = 0
        pal[i * 3 + 2] = 255 - i
    return bytes(pal)


def build_colormap() -> bytes:
    """Identity remap on every light level, so indices map to themselves."""
    identity = bytes(range(256))
    return identity * 34


def build_patch(width: int, height: int, pixels: list[list[int]]) -> bytes:
    """A PATCH lump: header, column offsets, then one post per column."""
    columns = []
    for x in range(width):
        col = bytes([0, height, 0]) + bytes(pixels[x]) + bytes([0, 0xFF])
        columns.append(col)

    header = struct.pack("<hhhh", width, height, 0, 0)
    offset = 8 + 4 * width
    offsets = []
    body = b""
    for col in columns:
        offsets.append(offset + len(body))
        body += col
    return header + struct.pack(f"<{width}I", *offsets) + body


def build_dmx(samples: bytes, rate: int = 11025) -> bytes:
    """DMX lump: format 3, rate, count, then 16 pad + samples + 16 pad."""
    payload = bytes(16) + samples + bytes(16)
    return struct.pack("<HHI", 3, rate, len(payload)) + payload


def build_mus() -> bytes:
    """One note: on at tick 0, off at tick 24, then score end."""
    events = bytes(
        [
            0x90, 0x3C,  # play note, channel 0, last event
            0x18,        # delta: 24 ticks
            0x00, 0x3C,  # release note, channel 0
            0x60,        # score end
        ]
    )
    header = b"MUS\x1a" + struct.pack("<6H", len(events), 16, 0, 0, 0, 0)
    return header + events


def build_wad(lumps: list[tuple[str, bytes]]) -> bytes:
    """Write an IWAD: header, lump data, directory."""
    data = b""
    directory = b""
    offset = 12
    for name, payload in lumps:
        directory += struct.pack("<ii8s", offset, len(payload), name.encode("ascii"))
        data += payload
        offset += len(payload)
    header = struct.pack("<4sii", b"IWAD", len(lumps), 12 + len(data))
    return header + data + directory


def make_wad() -> bytes:
    flat = bytes(64 * 64)  # all index 0
    patch = build_patch(2, 2, [[1, 2], [3, 4]])
    samples = bytes(range(100))
    return build_wad(
        [
            ("PLAYPAL", build_palette()),
            ("COLORMAP", build_colormap()),
            ("P_START", b""),
            ("TESTPIC", patch),
            ("P_END", b""),
            ("F_START", b""),
            ("FLOOR0_1", flat),
            ("F_END", b""),
            ("DSFOO", build_dmx(samples)),
            ("D_FOO", build_mus()),
        ]
    )


# ------------------------------------------------------------------------ tests


def test_wad(path: Path) -> None:
    wad = Wad(path)

    print("wad structure")
    check_equal("magic", wad.magic, "IWAD")
    check_equal("lump count", wad.numlumps, 10)
    check("lookup by name", "PLAYPAL" in wad)
    check("missing lump raises", "NOPE" not in wad)
    check_equal("sprite namespace is empty", wad.sprite_names, [])
    check_equal("flat namespace", wad.flat_names, ["FLOOR0_1"])

    print("palette")
    table = wad.palette_table(0)
    check_equal("palette entry 0", tuple(table[0:3]), (0, 0, 255))
    check_equal("palette entry 255", tuple(table[255 * 3 : 255 * 3 + 3]), (255, 0, 0))

    print("patch")
    w, h, left, top, rows = wad.raw_patch("TESTPIC")
    check_equal("patch size", (w, h), (2, 2))
    check_equal("patch origin", (left, top), (0, 0))
    check_equal("patch column 0", [rows[0][0], rows[0][1]], [1, 2])
    check_equal("patch column 1", [rows[1][0], rows[1][1]], [3, 4])

    img = wad.patch("TESTPIC")
    check_equal("patch image size", img.size, (2, 2))
    check_equal("patch pixel (0,0) is index 1", img.getpixel((0, 0)), (1, 0, 254, 255))
    check_equal("patch pixel (1,1) is index 4", img.getpixel((1, 1)), (4, 0, 251, 255))

    print("flat")
    flat = wad.flat("FLOOR0_1")
    check_equal("flat size", flat.size, (64, 64))
    check_equal("flat colour is palette[0]", flat.getpixel((0, 0)), (0, 0, 255, 255))


def test_audio(path: Path) -> None:
    wad = Wad(path)

    print("dmx")
    wav_bytes = dmx_to_wav(wad.bytes("DSFOO"))
    with wave.open(io.BytesIO(wav_bytes)) as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        width = wf.getsampwidth()
        channels = wf.getnchannels()
        pcm = np.frombuffer(wf.readframes(frames), dtype="<i2")

    check_equal("wav is mono", channels, 1)
    check_equal("wav is 16-bit", width, 2)
    check_equal("wav sample rate", rate, 11025)
    check_equal("wav frame count equals DMX count-32", frames, 100)

    # Mid-sample must survive the de-click fade and the 8-bit -> 16-bit map.
    want = (50 - 128) / 127.5 * 32767
    check(
        "decoded amplitude",
        abs(int(pcm[50]) - want) < 2,
        f"(got {int(pcm[50])}, want {want:.0f})",
    )

    print("mus")
    song = parse_mus(wad.bytes("D_FOO"))
    check_equal("note count", len(song.notes), 1)
    note = song.notes[0]
    check_equal("note pitch", note.pitch, 60)
    check_equal("note channel", note.channel, 0)
    check("note starts at 0", abs(note.start) < 1e-9, f"(got {note.start})")
    check(
        "note length is 24 ticks at 140 Hz",
        abs((note.stop - note.start) - 24 / 140) < 1e-6,
        f"(got {note.stop - note.start})",
    )


def main() -> int:
    payload = make_wad()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "selftest.wad"
        path.write_bytes(payload)
        print(f"synthetic WAD: {len(payload)} bytes")
        test_wad(path)
        test_audio(path)

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {', '.join(FAILURES)}")
        return 1
    print("all wadlib checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())