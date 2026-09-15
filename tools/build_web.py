#!/usr/bin/env python3
"""
Build the dogorcat.net static site from the game's own species list.

SPECIES in dogorcat.py is the single source of truth. This script reads it,
collects each photo's photographer and licence from Wikimedia, re-encodes the
images at web sizes, and writes the generated half of docs/:

    docs/data/species.json      what the game loads
    docs/photos/<hash>-660.webp the pictures, including credits thumbnails
    docs/assets/og-card.png     the link preview card

The hand-written half of docs/ -- index.html, credits.html, css/, js/ -- is
never touched. credits.html builds its list from species.json in the browser,
so that it can show only the photographs the player has actually been shown.

Photo filenames are hashes rather than species names on purpose: the src is
visible in the DOM and in devtools, so "gray-wolf-660.webp" would give the
answer away before the guess. The hash is of the source image, so a photo that
changes gets a new URL, which is the only cache control GitHub Pages allows.

Usage:
    python3 tools/build_web.py                 build (uses caches, no downloads)
    python3 tools/build_web.py --refresh-meta  re-read every licence from Commons
    python3 tools/build_web.py --check-free    verify licences and stop
"""

import argparse
import hashlib
import html
import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dogorcat                                       # noqa: E402
from overrides import OVERRIDES                       # noqa: E402

DOCS = ROOT / "docs"
PHOTO_DIR = DOCS / "photos"
WEB_CACHE = dogorcat.CACHE_DIR / "web"

DISPLAY_WIDTHS = (1280, 660)   # what the game shows, for srcset
THUMB_WIDTH = 320              # the credits page
WARN_WIDTH = 1280              # softer than we would like
MIN_WIDTH = 660                # refuse outright

FREE_PREFIXES = ("cc", "public domain", "pd", "no restrictions")
UNFREE = re.compile(r"fair use|non-free|all rights reserved|copyrighted free",
                    re.I)


# ---------------------------------------------------------------- text

def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def plain(markup):
    """
    Flatten a Wikimedia extmetadata HTML field to readable text.

    Artist arrives in at least four shapes: bare text, a redlink <a>, a nested
    <bdi><a><span>, and "Marton Berntsen<br>crop by User:MPF". The <br> has to
    become a space before the tags go, or two names run together, and the
    entities have to be unescaped after, so that an entity inside an attribute
    can never turn into a tag.
    """
    if not markup:
        return ""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", markup)
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" ,;|")


def licence_problem(meta):
    """Why this photo may not be published, or None if it is fine."""
    licence = (meta.get("license") or "").strip()
    if meta.get("restrictions"):
        return "restricted: " + plain(meta["restrictions"])
    if meta.get("repository") == "local":
        return "hosted locally on Wikipedia, not Commons (usually fair use)"
    if not licence:
        return "no licence stated"
    if UNFREE.search(licence):
        return "not a free licence: " + licence
    if not licence.lower().startswith(FREE_PREFIXES):
        return "unrecognised licence: " + licence
    return None


# ---------------------------------------------------------------- images

def source_image(lib, meta):
    """The 1280-wide render from Commons, cached on disk between builds."""
    url = meta.get("thumb_url") or ""
    if not url:
        raise RuntimeError("no image URL")
    WEB_CACHE.mkdir(parents=True, exist_ok=True)
    path = WEB_CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".img")
    if path.exists():
        raw = path.read_bytes()
    else:
        raw = lib._get(url).content
        path.write_bytes(raw)
    image = Image.open(io.BytesIO(raw))
    image.load()
    return image.convert("RGB"), hashlib.sha1(raw).hexdigest()[:10]


def can_avif():
    try:
        import pillow_avif  # noqa: F401
        return True
    except ImportError:
        return "AVIF" in {f for f in Image.registered_extensions().values()}


def encode(image, stem, width, formats):
    """Write one width in every available format. Never upscales."""
    width = min(width, image.width)
    height = max(1, round(image.height * width / image.width))
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    for ext in formats:
        out = PHOTO_DIR / ("%s-%d.%s" % (stem, width, ext))
        if not out.exists():
            if ext == "webp":
                resized.save(out, "WEBP", quality=80, method=6)
            else:
                resized.save(out, "AVIF", quality=55, speed=4)
    return width, height


# ---------------------------------------------------------------- pages

def font(size, bold=True):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
                 if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_og_card(images):
    """A 1200x630 title card for link previews. Never a species photo alone."""
    card = Image.new("RGB", (1200, 630), "#12151c")
    strip_h = 250
    for i, im in enumerate(images[:4]):
        tile = im.copy()
        scale = max(300 / tile.width, strip_h / tile.height)
        tile = tile.resize((max(1, round(tile.width * scale)),
                            max(1, round(tile.height * scale))),
                           Image.Resampling.LANCZOS)
        left = max(0, (tile.width - 300) // 2)
        top = max(0, (tile.height - strip_h) // 2)
        card.paste(tile.crop((left, top, left + 300, top + strip_h)),
                   (i * 300, 630 - strip_h))

    draw = ImageDraw.Draw(card)
    draw.text((70, 150), "Dog or Cat?", font=font(96), fill="#eef1f7")
    draw.text((70, 268), "Caniformia or Feliformia — which branch?",
              font=font(38, bold=False), fill="#8792a8")
    draw.text((70, 336), "dogorcat.net", font=font(30), fill="#2f8f5b")
    draw.rectangle((0, 630 - strip_h - 3, 1200, 630 - strip_h), fill="#2f8f5b")
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)
    card.save(DOCS / "assets" / "og-card.png")


# ---------------------------------------------------------------- build

def build(refresh_meta=False, check_only=False):
    lib = dogorcat.PhotoLibrary()
    titles = [s["title"] for s in dogorcat.SPECIES]

    print("reading licences for %d species…" % len(titles))
    meta = lib.metadata_many(titles, refresh=refresh_meta, names=OVERRIDES)

    problems = []
    for species in dogorcat.SPECIES:
        m = meta.get(species["title"])
        if not m:
            problems.append((species["name"], "no photo found"))
            continue
        why = licence_problem(m)
        if why:
            problems.append((species["name"], why))
    if problems:
        print("\nREFUSING TO PUBLISH — these photos are not clearly free:")
        for name, why in problems:
            print("  %-26s %s" % (name, why))
        print("\nPin a different Commons file in tools/overrides.py, or drop "
              "the species.")
        return 1
    print("all %d photos are freely licensed" % len(meta))
    if check_only:
        return 0

    formats = ["webp"] + (["avif"] if can_avif() else [])
    if "avif" not in formats:
        print("note: no AVIF encoder here, shipping WebP only "
              "(install pillow-avif-plugin to add it)")

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS / "data").mkdir(parents=True, exist_ok=True)

    entries, keep, samples, warnings = [], set(), [], []
    for i, species in enumerate(dogorcat.SPECIES, 1):
        m = meta[species["title"]]
        image, stem = source_image(lib, m)

        if image.width < MIN_WIDTH:
            print("\n%s: source is only %d px wide, below the %d px floor."
                  % (species["name"], image.width, MIN_WIDTH))
            print("Pin a bigger Commons file in tools/overrides.py.")
            return 1
        if image.width < WARN_WIDTH:
            warnings.append((species["name"], image.width))

        sizes = {}
        for width in DISPLAY_WIDTHS:
            w, h = encode(image, stem, width, formats)
            sizes[w] = h
        tw, th = encode(image, stem, THUMB_WIDTH, formats)
        for width in list(sizes) + [tw]:
            for ext in formats:
                keep.add("%s-%d.%s" % (stem, width, ext))

        entries.append({
            "id": slug(species["name"]),
            "name": species["name"],
            "side": species["side"],
            "family": species["family"],
            "fact": species["fact"],
            "tricky": species["tricky"],
            "wiki": "https://en.wikipedia.org/wiki/" + species["title"],
            "photo": {
                "stem": "photos/" + stem,
                "widths": sorted(sizes),
                "height": {str(w): h for w, h in sizes.items()},
                "formats": formats,
                "thumb": "photos/%s-%d.%s" % (stem, tw, formats[0]),
                "thumb_width": tw, "thumb_height": th,
            },
            "credit": {
                "artist": plain(m["artist_html"]),
                "artist_html": m["artist_html"],
                "license": m["license"],
                "license_url": m["license_url"],
                "attribution_required": m["attribution_required"] == "true",
                "file_name": m["file_name"],
                "file_page": m["file_page"],
            },
        })
        # Four photos spread evenly through the list, which is ordered
        # Caniformia then Feliformia, so the card shows both branches.
        if i - 1 in {round(len(dogorcat.SPECIES) * k / 8) for k in (1, 3, 5, 7)}:
            samples.append(image)
        print("  %2d/%d  %-26s %5dpx  %s"
              % (i, len(dogorcat.SPECIES), species["name"], image.width,
                 m["license"]))

    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rounds": dogorcat.ROUNDS,
        "count": len(entries),
        "species": entries,
    }
    (DOCS / "data" / "species.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False))

    write_og_card(samples or [Image.new("RGB", (300, 250), "#1a1f2b")])

    stale = [p for p in PHOTO_DIR.iterdir() if p.name not in keep]
    for path in stale:
        path.unlink()
    if stale:
        print("removed %d photo file(s) no longer referenced" % len(stale))

    if warnings:
        print("\nsources narrower than %d px (soft on a retina screen):"
              % WARN_WIDTH)
        for name, width in sorted(warnings, key=lambda x: x[1]):
            print("  %-26s %d px" % (name, width))

    for required in (DOCS / "CNAME", DOCS / ".nojekyll"):
        if not required.exists():
            print("\nWARNING: %s is missing. Without CNAME the custom domain "
                  "detaches; without .nojekyll, Jekyll eats the site."
                  % required.name)

    total = sum(p.stat().st_size for p in PHOTO_DIR.iterdir())
    print("\n%d species, %d photo files, %.1f MB"
          % (len(entries), len(keep), total / 1e6))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--refresh-meta", action="store_true",
                    help="re-read every licence from Commons")
    ap.add_argument("--check-free", action="store_true",
                    help="verify the licences and stop, building nothing")
    args = ap.parse_args()
    started = time.time()
    code = build(refresh_meta=args.refresh_meta, check_only=args.check_free)
    print("%s in %.1fs" % ("failed" if code else "done", time.time() - started))
    return code


if __name__ == "__main__":
    sys.exit(main())
