#!/usr/bin/env python3
"""Generate .webp versions of images in specified directories.

This script scans one or more directories for common image files and
creates a same-named .webp file next to each original image unless the
webp already exists.

Usage:
  python scripts/generate_webp.py            # run on defaults (NPjpgs and vodstvo)
  python scripts/generate_webp.py --dirs NPjpgs vodstvo --quality 85 --force

The script is idempotent and safe to run repeatedly.
Requires Pillow (already in requirements.txt).
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable
import sys

try:
    from PIL import Image
except Exception as e:
    print("Pillow is required. Install it with: pip install Pillow")
    raise


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"}


def find_images(folder: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                yield p
    else:
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                yield p


def make_webp(src: Path, dest: Path, quality: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Open and save as WEBP; preserve alpha where present
    with Image.open(src) as im:
        # Pillow supports saving RGBA as WEBP
        save_kwargs = {"quality": quality}
        # If image is paletted, convert to RGBA to avoid issues
        if im.mode in ("P",):
            im = im.convert("RGBA")
        # For JPEG-like images ensure RGB
        if im.mode == "RGBA":
            # WEBP supports alpha; keep it
            im.save(dest, "WEBP", **save_kwargs)
        else:
            im = im.convert("RGB")
            im.save(dest, "WEBP", **save_kwargs)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate .webp images next to originals")
    p.add_argument("--dirs", "-d", nargs="+", default=["NPjpgs", "vodstvo"], help="Directories to scan")
    p.add_argument("--quality", "-q", type=int, default=85, help="WebP quality (default 85)")
    p.add_argument("--recursive", "-r", action="store_true", help="Recurse into subfolders")
    p.add_argument("--force", "-f", action="store_true", help="Overwrite existing .webp files")

    args = p.parse_args(argv)

    total = 0
    created = 0
    for d in args.dirs:
        folder = Path(d)
        if not folder.exists() or not folder.is_dir():
            print(f"Warning: skipping missing folder: {folder}")
            continue
        files = list(find_images(folder, args.recursive))
        print(f"Scanning {folder} — found {len(files)} image(s)")
        for src in files:
            total += 1
            dest = src.with_suffix('.webp')
            if dest.exists() and not args.force:
                # skip
                continue
            try:
                make_webp(src, dest, args.quality)
                created += 1
                print(f"Created: {dest}")
            except Exception as exc:
                print(f"Failed to create {dest}: {exc}")

    print(f"Done. Scanned {total} images, created {created} webp(s)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
