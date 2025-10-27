#!/usr/bin/env python3
"""Resize all image files in a specified folder to the same dimensions.

Usage examples:
  python tools/resize_images.py --input "vodstvo" --output "res" --width 128 --height 128 --to-webp
  python tools/resize_images.py -i src/images -o out -w 800 -h 600 --recursive

Features:
- Resizes images in a folder (optionally recursively)
- Keeps directory structure in output folder
- Optionally preserves aspect ratio (default) or forces exact dimensions
- Optionally converts output to WEBP and sets quality

Requires: Pillow (install with `pip install Pillow` or add to requirements.txt)
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, Tuple, Optional

try:
    from PIL import Image
except Exception as e:  # pragma: no cover - helpful message when Pillow missing
    raise SystemExit(
        "Pillow is required. Install it with: pip install Pillow\nOriginal error: {}".format(e)
    )


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}


def find_images(folder: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                yield p
    else:
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                yield p


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resize_image(
    src: Path,
    dest: Path,
    size: Optional[Tuple[int, int]],
    keep_aspect: bool = True,
    force: bool = False,
    to_webp: bool = False,
    quality: int = 85,
) -> None:
    """Open src image, resize according to options, and save to dest."""
    with Image.open(src) as im:
        # Convert images with palette to RGBA to preserve transparency when needed
        if im.mode in ("P",):
            im = im.convert("RGBA")

        ensure_parent(dest)
        save_kwargs = {}
        out_suffix = dest.suffix.lower()
        out_format = None

        if to_webp:
            out_format = "WEBP"
            save_kwargs["quality"] = quality
        else:
            # infer format from dest suffix or leave to PIL to decide
            if out_suffix in (".jpg", ".jpeg"):
                out_format = "JPEG"
                save_kwargs["quality"] = quality
            elif out_suffix == ".png":
                out_format = "PNG"

        if size is None:
            # No resize requested — just convert/copy while handling alpha for JPEG
            final = im
            if final.mode == "RGBA" and out_format in ("JPEG",):
                bg = Image.new("RGB", final.size, (255, 255, 255))
                bg.paste(final, mask=final.split()[-1])
                final = bg
            if out_format:
                final.save(dest, out_format, **save_kwargs)
            else:
                final.save(dest)
            return

        # Resize flow
        if force:
            resized = im.resize(size, Image.LANCZOS)
        else:
            # thumbnail preserves aspect ratio and doesn't upsize by default
            resized = im.copy()
            resized.thumbnail(size, Image.LANCZOS)

        # Preserve transparency when appropriate
        if resized.mode == "RGBA" and out_format in ("PNG", "WEBP"):
            pass
        elif resized.mode == "RGBA" and out_format in ("JPEG",):
            # JPEG doesn't support alpha; convert to RGB with white background
            bg = Image.new("RGB", resized.size, (255, 255, 255))
            bg.paste(resized, mask=resized.split()[-1])
            resized = bg

        # Final save
        if out_format:
            resized.save(dest, out_format, **save_kwargs)
        else:
            resized.save(dest)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Resize images in a folder to the same dimensions")
    p.add_argument("--input", "-i", required=True, help="Input folder containing images")
    p.add_argument("--output", "-o", required=True, help="Output folder for resized images")
    p.add_argument("--width", "-w", type=int, required=False, help="Target width in pixels")
    # -h is reserved for help by argparse, use -H as the short option for height
    p.add_argument("--height", "-H", type=int, required=False, help="Target height in pixels")
    p.add_argument(
        "--no-resize",
        "-n",
        action="store_true",
        help="Do not resize images; only convert/copy to output format (e.g., WebP)",
    )
    p.add_argument("--recursive", "-r", action="store_true", help="Recurse into subfolders")
    p.add_argument(
        "--force",
        action="store_true",
        help="Force exact width/height (may change aspect ratio). By default aspect ratio is preserved",
    )
    p.add_argument(
        "--to-webp", action="store_true", help="Convert output images to WebP format (keeps .webp extension)"
    )
    p.add_argument("--quality", "-q", type=int, default=85, help="Quality for lossy formats (default: 85)")

    args = p.parse_args(argv)

    in_folder = Path(args.input)
    out_folder = Path(args.output)
    # Validate input folder
    if not in_folder.exists() or not in_folder.is_dir():
        print(f"Input folder does not exist or is not a directory: {in_folder}")
        return 2

    # If resizing is requested, width and height are required
    if not args.no_resize and (args.width is None or args.height is None):
        p.error("--width and --height are required unless --no-resize is specified")

    size = None if args.no_resize else (args.width, args.height)

    files = list(find_images(in_folder, args.recursive))
    if not files:
        print("No image files found in the input folder.")
        return 0

    print(f"Found {len(files)} image(s). Resizing to {size} (force={args.force})...")

    for src in files:
        rel = src.relative_to(in_folder)
        dest_suffix = ".webp" if args.to_webp else src.suffix
        dest = out_folder.joinpath(rel).with_suffix(dest_suffix)
        try:
            resize_image(
                src,
                dest,
                size,
                keep_aspect=not args.force,
                force=args.force,
                to_webp=args.to_webp,
                quality=args.quality,
            )
            print(f"OK: {src} -> {dest}")
        except Exception as exc:
            print(f"ERROR processing {src}: {exc}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
