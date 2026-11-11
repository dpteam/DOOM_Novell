"""Quick WAD inspector: lists lump namespaces and lump counts.

Usage:
    python tools/wadinfo.py <path-to-wad> [--grep PATTERN] [--list]

This is a small developer helper used while building the asset pipeline.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


def read_directory(path: Path):
    data = path.read_bytes()
    if len(data) < 12:
        raise SystemExit("not a WAD file (too short)")
    magic, numlumps, diroffset = struct.unpack_from("<4sii", data, 0)
    magic = magic.decode("ascii", "replace")
    if magic not in ("IWAD", "PWAD"):
        raise SystemExit(f"unexpected WAD magic: {magic!r}")
    lumps = []
    for i in range(numlumps):
        off, size, name = struct.unpack_from("<ii8s", data, diroffset + i * 16)
        lumps.append((name.split(b"\0")[0].decode("latin-1"), off, size))
    return magic, lumps


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("wad")
    ap.add_argument("--grep", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--namespaces", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.wad)
    magic, lumps = read_directory(path)
    total = sum(size for _, _, size in lumps)
    print(f"{path.name}: {magic}, {len(lumps)} lumps, {total / 1048576:.2f} MiB")
    first = lumps[0]
    print(f"first lump: {first[0]!r} ({first[2]} bytes)")

    if args.grep:
        pat = args.grep.upper()
        hits = [(n, s) for n, _, s in lumps if pat in n.upper()]
        print(f"{len(hits)} lumps match {pat!r}")
        for n, s in hits:
            print(f"  {n:8s} {s:8d}")

    if args.list:
        for n, o, s in lumps:
            print(f"{o:9d} {s:8d} {n}")

    if args.namespaces:
        prefixes = {}
        for n, _, _ in lumps:
            key = "".join(ch for ch in n if not ch.isdigit())[:3]
            prefixes[key] = prefixes.get(key, 0) + 1
        for k, v in sorted(prefixes.items(), key=lambda kv: -kv[1])[:40]:
            print(f"  {k:4s} {v}")


if __name__ == "__main__":
    sys.exit(main())