"""Assemble a build tree from FreeDoom-derived assets, then run the checks.

CI uses this same idea: copy the source tree, swap the generated assets for
ones rebuilt from FreeDoom, and verify the result.  Doing it here locally
proves the pipeline is actually FreeDoom-clean before a release depends on it.

    python tools/make_freedoom_build.py --assets <dir> --out <dir>
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Generated content that is replaced wholesale.
SWAP = [
    "game/images",
    "game/gui",
    "game/audio",
    "game/fonts",
    "game/wad_manifest.json",
]

# Things a build never needs.  `tools/` stays: gen_images_rpy.py and
# verify_assets.py live there and resolve paths relative to their own location,
# so the copy must contain them.  options.rpy already excludes tools/ from the
# packaged game.
SKIP = {
    ".git",
    ".github",
    "dist",
    "tests",
    "refs",
    "__pycache__",
    ".venv",
}


def copytree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in SKIP:
            continue
        target = dst / item.name
        if item.is_dir():
            copytree(item, target)
        else:
            shutil.copy2(item, target)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True, help="tree built by build_assets.py")
    ap.add_argument("--out", required=True, help="where to assemble the project")
    args = ap.parse_args(argv)

    assets = Path(args.assets).resolve()
    out = Path(args.out).resolve()

    if out.exists():
        shutil.rmtree(out)

    print(f"copying sources to {out}")
    copytree(ROOT, out)

    for rel in SWAP:
        src = assets / rel
        dst = out / rel
        if not src.exists():
            print(f"! missing in asset tree: {rel}")
            return 1
        if dst.is_dir():
            shutil.rmtree(dst)
        elif dst.exists():
            dst.unlink()
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"  swapped {rel}")

    # Regenerate the image declarations for the new set.
    print("regenerating images.rpy")
    subprocess.run(
        [sys.executable, str(out / "tools" / "gen_images_rpy.py")],
        check=True,
        cwd=out,
    )

    print("verifying")
    result = subprocess.run(
        [sys.executable, str(out / "tools" / "verify_assets.py")],
        cwd=out,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
