#!/usr/bin/env python3
"""
Dog or Cat?

A guessing game about the two great branches of the order Carnivora:

    Caniformia  -- the "dog-like" carnivorans
    Feliformia  -- the "cat-like" carnivorans

The catch is that these are suborders, not families, and they are much
wider than their nicknames suggest. Seals, bears, otters, raccoons and
skunks are all dog-like. Hyenas, mongooses, meerkats and civets are all
cat-like. So a game that sounds like a coin flip is not one.

Photos are fetched from Wikipedia at runtime and cached in
~/.cache/dog-or-cat/ so later rounds are instant and work offline.

Usage:
    python3 dogorcat.py            play
    python3 dogorcat.py --check    verify every species photo resolves
"""

import hashlib
import io
import json
import queue
import random
import re
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

import requests
from PIL import Image, ImageTk

# --------------------------------------------------------------------------
# The animals
# --------------------------------------------------------------------------
# "title" is the English Wikipedia article, which is where the photo and the
# name come from. "family" is the actual family inside the suborder -- that is
# the part that makes the reveal worth reading.

DOG = "dog"  # Caniformia
CAT = "cat"  # Feliformia


def a(title, name, side, family, fact, tricky=False):
    return {
        "title": title,
        "name": name,
        "side": side,
        "family": family,
        "fact": fact,
        "tricky": tricky,
    }


SPECIES = [
    # ---------------- Caniformia: the dog-like carnivorans ----------------
    # Canidae -- the actual dogs, for the people who need a win
    a("Gray_wolf", "Gray wolf", DOG, "Canidae",
      "Every domestic dog alive descends from an ancient population of these."),
    a("Red_fox", "Red fox", DOG, "Canidae",
      "Dives nose-first into snow after mice, and appears to line the jump up "
      "using Earth's magnetic field."),
    a("Fennec_fox", "Fennec fox", DOG, "Canidae",
      "Ears up to 15 cm long, the largest of any canid relative to body size, "
      "and they work as radiators."),
    a("Arctic_fox", "Arctic fox", DOG, "Canidae",
      "The warmest coat of any mammal. It does not start shivering until "
      "about -70 C."),
    a("African_wild_dog", "African wild dog", DOG, "Canidae",
      "Packs decide when to set off hunting by sneezing. Enough sneezes and "
      "the vote carries."),
    a("Bat-eared_fox", "Bat-eared fox", DOG, "Canidae",
      "Listens for termites underground and has up to 50 teeth, more than any "
      "other placental land mammal."),
    a("Dhole", "Dhole", DOG, "Canidae",
      "An Asian wild dog that whistles to keep the pack together."),
    a("Maned_wolf", "Maned wolf", DOG, "Canidae",
      "Not a wolf and not a fox, but a long-legged canid all of its own. Its "
      "urine smells strongly of cannabis.", tricky=True),
    a("Raccoon_dog", "Raccoon dog", DOG, "Canidae",
      "A true canid wearing a raccoon's face. The only one that climbs trees "
      "and sleeps through the winter.", tricky=True),

    # Ursidae -- bears are dog-like
    a("Brown_bear", "Brown bear", DOG, "Ursidae",
      "Bears sit on the dog-like branch of Carnivora, closest to seals and "
      "weasels."),
    a("Polar_bear", "Polar bear", DOG, "Ursidae",
      "The fur is transparent rather than white, and the skin underneath is "
      "black."),
    a("Giant_panda", "Giant panda", DOG, "Ursidae",
      "A bear running a 99% bamboo diet on a carnivore's gut, which is why it "
      "must eat up to 38 kg of it a day.", tricky=True),
    a("Sun_bear", "Sun bear", DOG, "Ursidae",
      "The smallest bear, with a 25 cm tongue for emptying honeycombs and "
      "termite nests."),
    a("Sloth_bear", "Sloth bear", DOG, "Ursidae",
      "Missing its two upper front teeth, leaving a gap it uses to vacuum "
      "termites out of their mounds."),

    # Mustelidae -- weasels and otters
    a("Wolverine", "Wolverine", DOG, "Mustelidae",
      "A 15 kg weasel with the confidence to drive bears off a carcass."),
    a("Sea_otter", "Sea otter", DOG, "Mustelidae",
      "The densest fur of any animal, up to a million hairs per square inch, "
      "and it holds hands while sleeping."),
    a("Honey_badger", "Honey badger", DOG, "Mustelidae",
      "Loose rubbery skin lets it rotate inside its own hide and bite whatever "
      "has it by the neck."),
    a("European_badger", "European badger", DOG, "Mustelidae",
      "Digs setts that stay in use by generation after generation for over a "
      "century."),
    a("Stoat", "Stoat", DOG, "Mustelidae",
      "Turns white in winter, at which point the coat gets sold as ermine."),
    a("Eurasian_otter", "Eurasian otter", DOG, "Mustelidae",
      "Otters are aquatic weasels, and weasels are firmly on the dog-like "
      "branch."),
    a("Pine_marten", "Pine marten", DOG, "Mustelidae",
      "Cat-shaped, cat-sized, cat-agile, and a mustelid.", tricky=True),

    # Procyonidae -- raccoons and relatives
    a("Raccoon", "Raccoon", DOG, "Procyonidae",
      "Its front paws carry four times the touch receptors of the hind ones. "
      "It largely sees by feel."),
    a("Kinkajou", "Kinkajou", DOG, "Procyonidae",
      "A carnivoran that mostly eats fruit, hangs by a prehensile tail, and "
      "pollinates flowers with a 13 cm tongue.", tricky=True),
    a("South_American_coati", "South American coati", DOG, "Procyonidae",
      "Females and young roam in bands of up to 30 while adult males live "
      "alone."),
    a("Ring-tailed_cat", "Ringtail", DOG, "Procyonidae",
      "Nicknamed the miner's cat and the ring-tailed cat. It is a raccoon "
      "relative and no kind of cat.", tricky=True),

    # Mephitidae -- skunks
    a("Striped_skunk", "Striped skunk", DOG, "Mephitidae",
      "Sprays accurately to about 3 metres, but stamps its front feet in "
      "warning first.", tricky=True),

    # Ailuridae -- the red panda, alone
    a("Red_panda", "Red panda", DOG, "Ailuridae",
      "Not a bear, not a raccoon, and not related to the giant panda. The only "
      "living member of its family, and it sits on the dog-like branch.",
      tricky=True),

    # Pinnipeds -- seals, sea lions and the walrus are dog-like too
    a("Harbor_seal", "Harbour seal", DOG, "Phocidae",
      "Its whiskers can follow the wake a fish left behind up to 30 seconds "
      "earlier.", tricky=True),
    a("Leopard_seal", "Leopard seal", DOG, "Phocidae",
      "Named for a cat, related to weasels and bears. It sings underwater for "
      "hours at a time.", tricky=True),
    a("Northern_elephant_seal", "Northern elephant seal", DOG, "Phocidae",
      "Dives to 1,500 m and can stay under for nearly two hours.", tricky=True),
    a("California_sea_lion", "California sea lion", DOG, "Otariidae",
      "Unlike true seals it can swing its hind flippers forward and gallop on "
      "land.", tricky=True),
    a("Walrus", "Walrus", DOG, "Odobenidae",
      "Those tusks are canine teeth up to a metre long, used to haul two "
      "tonnes of walrus onto the ice.", tricky=True),

    # ---------------- Feliformia: the cat-like carnivorans ----------------
    # Felidae -- the actual cats
    a("Lion", "Lion", CAT, "Felidae",
      "The only cat that lives in groups. The roar carries about 8 km."),
    a("Tiger", "Tiger", CAT, "Felidae",
      "The stripes are on the skin as well as the fur. Shave one and the "
      "pattern is still there."),
    a("Cheetah", "Cheetah", CAT, "Felidae",
      "Semi-retractable claws act as sprint spikes. Nought to 100 km/h in "
      "about three seconds."),
    a("Snow_leopard", "Snow leopard", CAT, "Felidae",
      "Cannot roar, and uses its metre-long tail as a blanket."),
    a("Jaguar", "Jaguar", CAT, "Felidae",
      "The strongest bite of any big cat for its size. It kills by punching "
      "through the skull."),
    a("Serval", "Serval", CAT, "Felidae",
      "The longest legs of any cat relative to its body, and it leaps 3 m to "
      "pluck birds out of the air."),
    a("Caracal", "Caracal", CAT, "Felidae",
      "Twenty muscles in each tufted ear, and it knocks birds down mid-leap."),
    a("Sand_cat", "Sand cat", CAT, "Felidae",
      "Fur-covered foot pads let it cross 60 C sand, and it never needs to "
      "drink."),
    a("Clouded_leopard", "Clouded leopard", CAT, "Felidae",
      "Canines as long as a tiger's relative to its skull, and it can climb "
      "down a trunk head-first."),
    a("Black-footed_cat", "Black-footed cat", CAT, "Felidae",
      "Africa's smallest cat and its deadliest. Roughly 60% of its hunts "
      "succeed."),
    a("Ocelot", "Ocelot", CAT, "Felidae",
      "A cat that swims willingly, which most of the family will not."),
    a("Eurasian_lynx", "Eurasian lynx", CAT, "Felidae",
      "Europe's third largest predator, and the ear tufts work as hearing "
      "aids."),
    a("Cougar", "Cougar", CAT, "Felidae",
      "Cannot roar but purrs like a house cat, and holds the record for the "
      "most names of any animal."),
    a("Fishing_cat", "Fishing cat", CAT, "Felidae",
      "Taps the water surface to imitate insects, then dives in after the fish "
      "that come to look."),

    # Hyaenidae -- hyenas are cat-like, which is the single best fact here
    a("Spotted_hyena", "Spotted hyena", CAT, "Hyaenidae",
      "Far closer to cats than to dogs. Clans are run by females, and every "
      "female outranks every male.", tricky=True),
    a("Striped_hyena", "Striped hyena", CAT, "Hyaenidae",
      "Hyenas branched off the cat-like side of Carnivora. The dog resemblance "
      "is pure convergent evolution.", tricky=True),
    a("Aardwolf", "Aardwolf", CAT, "Hyaenidae",
      "A hyena, therefore a cat-like carnivoran, despite the name. It eats up "
      "to 300,000 termites a night.", tricky=True),

    # Herpestidae -- mongooses
    a("Meerkat", "Meerkat", CAT, "Herpestidae",
      "A mongoose, not a cat, whatever the name says. Sentries use different "
      "alarm calls for hawks and for snakes.", tricky=True),
    a("Banded_mongoose", "Banded mongoose", CAT, "Herpestidae",
      "Mongooses are cat-like carnivorans, and the whole pack gives birth on "
      "the same night."),
    a("Indian_grey_mongoose", "Indian grey mongoose", CAT, "Herpestidae",
      "Its acetylcholine receptors are shaped so that cobra venom cannot lock "
      "on."),

    # Viverridae -- civets, genets and the bearcat
    a("Binturong", "Binturong", CAT, "Viverridae",
      "Known as the bearcat, it is neither, and its scent glands smell "
      "convincingly of hot buttered popcorn.", tricky=True),
    a("Common_genet", "Common genet", CAT, "Viverridae",
      "Looks like a spotted cat but belongs to the civets, and can flatten "
      "itself through any gap its head fits.", tricky=True),
    a("Asian_palm_civet", "Asian palm civet", CAT, "Viverridae",
      "The animal behind kopi luwak coffee."),
    a("African_civet", "African civet", CAT, "Viverridae",
      "Its musk was a base note in perfume for centuries."),

    # Eupleridae -- Madagascar's own radiation
    a("Fossa_(animal)", "Fossa", CAT, "Eupleridae",
      "Madagascar's top predator. Looks like a puma crossed with a mongoose, "
      "and mongooses are the closer guess.", tricky=True),

    # Nandiniidae and Prionodontidae -- one species each, both cat-like
    a("African_palm_civet", "African palm civet", CAT, "Nandiniidae",
      "The only member of its family. Its lineage split off before every other "
      "cat-like carnivoran.", tricky=True),
    a("Banded_linsang", "Banded linsang", CAT, "Prionodontidae",
      "The closest living relative of the true cats, sitting in a family of "
      "its own.", tricky=True),
]

ROUNDS = 10

# --------------------------------------------------------------------------
# Photos
# --------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".cache" / "dog-or-cat"
URL_CACHE = CACHE_DIR / "urls.json"
NAME_CACHE = CACHE_DIR / "names.json"
META_CACHE = CACHE_DIR / "meta.json"
# Wikimedia's user-agent policy asks for a contact address and will rate-limit
# or block clients that do not identify themselves.
# https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
USER_AGENT = ("DogOrCat/1.0 (https://dogorcat.net; besse@birdsview.no) "
              "python-requests")
API = "https://en.wikipedia.org/w/api.php"

# Wikimedia only serves a fixed set of thumbnail widths to direct requests, so
# the width is left to the API, which rounds up to the nearest standard size.
# See https://www.mediawiki.org/wiki/Common_thumbnail_sizes
IMAGE_WIDTH = 960
WEB_IMAGE_WIDTH = 1280   # what the website exports at; also a standard size
BATCH = 50               # titles per API query
MIN_REQUEST_GAP = 0.6    # seconds between requests, to stay a polite client
RETRIES = 5

# Asking for only the fields we use keeps the imageinfo response small; the
# unfiltered extmetadata block also carries descriptions, dates and categories.
EXTMETA_FIELDS = ("Artist", "LicenseShortName", "LicenseUrl", "Credit",
                  "AttributionRequired", "Restrictions", "Copyrighted")


class PhotoLibrary:
    """Resolves Wikipedia articles to photos, with an on-disk cache."""

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._lock = threading.Lock()
        self._throttle_lock = threading.Lock()
        self._last_request = 0.0
        try:
            self._urls = json.loads(URL_CACHE.read_text())
        except Exception:
            self._urls = {}
        try:
            self._names = json.loads(NAME_CACHE.read_text())
        except Exception:
            self._names = {}
        try:
            self._meta = json.loads(META_CACHE.read_text())
        except Exception:
            self._meta = {}

    # -- http --------------------------------------------------------------
    def _throttle(self):
        """Keep a minimum gap between requests. Wikimedia throttles bursts."""
        with self._throttle_lock:
            gap = time.monotonic() - self._last_request
            if gap < MIN_REQUEST_GAP:
                time.sleep(MIN_REQUEST_GAP - gap)
            self._last_request = time.monotonic()

    def _get(self, url, **kwargs):
        """GET with throttling and backoff, retrying on rate limits."""
        last = None
        for attempt in range(RETRIES):
            self._throttle()
            try:
                r = self.session.get(url, timeout=30, **kwargs)
                if r.status_code in (429, 503):
                    last = requests.HTTPError(
                        "%s from %s" % (r.status_code, url))
                    if attempt == RETRIES - 1:
                        break
                    # Prefer the server's own advice over our guess.
                    try:
                        wait = float(r.headers.get("Retry-After", ""))
                    except ValueError:
                        wait = 0.0
                    time.sleep(max(wait, 2.0 * (2 ** attempt)))
                    continue
                r.raise_for_status()
                return r
            except requests.RequestException as exc:
                last = exc
                if attempt == RETRIES - 1:
                    break
                time.sleep(2.0 * (2 ** attempt))
        raise last

    # -- url resolution ----------------------------------------------------
    def _save_urls(self):
        try:
            URL_CACHE.write_text(json.dumps(self._urls, indent=1))
            NAME_CACHE.write_text(json.dumps(self._names, indent=1))
        except OSError:
            pass

    def resolve_many(self, titles):
        """
        Look up image URLs for many articles at once.

        One query per 50 titles rather than one per title, which keeps the
        whole game under a couple of API calls and well clear of rate limits.
        """
        with self._lock:
            missing = [t for t in dict.fromkeys(titles)
                       if t not in self._urls or t not in self._names]
        if not missing:
            return

        found, names = {}, {}
        for start in range(0, len(missing), BATCH):
            chunk = missing[start:start + BATCH]
            r = self._get(API, params={
                "action": "query", "format": "json", "formatversion": "2",
                "prop": "pageimages", "piprop": "thumbnail|name",
                "pithumbsize": str(IMAGE_WIDTH), "redirects": "1",
                "titles": "|".join(chunk),
            })
            data = r.json().get("query", {})

            # A requested title may be normalised and then redirected before it
            # reaches the page that actually holds the photo.
            aliases = {}
            for entry in data.get("normalized", []) + data.get("redirects", []):
                aliases[entry["from"]] = entry["to"]
            pages = {p["title"]: p for p in data.get("pages", [])}

            for title in chunk:
                final, seen = title, set()
                while final in aliases and final not in seen:
                    seen.add(final)
                    final = aliases[final]
                page = pages.get(final)
                source = (page or {}).get("thumbnail", {}).get("source")
                if source:
                    found[title] = source.split("?")[0]
                # The API knows the real Commons filename. Deriving it from the
                # URL instead goes wrong whenever the original is narrower than
                # the width we asked for, because then there is no thumbnail
                # path and no "960px-" prefix to strip.
                if (page or {}).get("pageimage"):
                    names[title] = page["pageimage"]

        if found or names:
            with self._lock:
                self._urls.update(found)
                self._names.update(names)
                self._save_urls()

    def resolve(self, title):
        """Return the image URL for an article, or None."""
        with self._lock:
            cached = self._urls.get(title)
        if cached:
            return cached
        self.resolve_many([title])
        with self._lock:
            return self._urls.get(title)

    # -- bytes -------------------------------------------------------------
    def _cache_path(self, url):
        return CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".img")

    def fetch(self, title):
        """Return (PIL.Image, credit) for an article. Raises on failure."""
        url = self.resolve(title)
        if not url:
            raise RuntimeError("no image for " + title)

        path = self._cache_path(url)
        if path.exists():
            raw = path.read_bytes()
        else:
            raw = self._get(url).content
            try:
                path.write_bytes(raw)
            except OSError:
                pass

        image = Image.open(io.BytesIO(raw))
        image.load()
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        return image, "Photo: Wikimedia Commons / " + self.filename(title)

    def filename(self, title):
        """The Commons filename behind an article's photo."""
        with self._lock:
            name = self._names.get(title)
        if name:
            return name
        # Fallback for a cache written before filenames were recorded.
        url = self.resolve(title) or ""
        return re.sub(r"^\d+px-", "", url.rsplit("/", 1)[-1])

    # -- licence metadata --------------------------------------------------
    def metadata_many(self, titles, refresh=False, names=None):
        """
        Return {article title: raw credit fields} for many articles at once.

        The desktop game only ever needed the photo. A public web page also
        has to say who took it and under what licence, which the CC licences
        require and the game's filename-only credit does not satisfy.

        Commons files are asked for through en.wikipedia.org rather than
        Commons itself: the page comes back flagged missing, because there is
        no *local* file, but with a full imageinfo block for the shared one.
        Keeping to one host means one session and one throttle.
        """
        names = names or {}
        # An overridden species never needs the pageimages lookup at all: the
        # caller has already named the file it wants.
        lookup = [t for t in dict.fromkeys(titles) if t not in names]
        if lookup:
            self.resolve_many(lookup)
        wanted = {t: names.get(t) or self.filename(t)
                  for t in dict.fromkeys(titles)}
        wanted = {t: n for t, n in wanted.items() if n}

        todo = sorted({n for n in wanted.values()
                       if refresh or "thumb_url" not in self._meta.get(n, {})})
        fetched = {}
        for start in range(0, len(todo), BATCH):
            chunk = todo[start:start + BATCH]
            r = self._get(API, params={
                "action": "query", "format": "json", "formatversion": "2",
                "prop": "imageinfo", "iiprop": "extmetadata|url|size",
                "iiurlwidth": str(WEB_IMAGE_WIDTH),
                "iiextmetadatafilter": "|".join(EXTMETA_FIELDS),
                "titles": "|".join("File:" + n for n in chunk),
            })
            data = r.json().get("query", {})
            aliases = {e["from"]: e["to"] for e in data.get("normalized", [])}
            pages = {p["title"]: p for p in data.get("pages", [])}

            for name in chunk:
                key = "File:" + name
                page = pages.get(aliases.get(key, key))
                info = (page or {}).get("imageinfo") or [{}]
                meta = info[0].get("extmetadata", {})

                def field(key):
                    return (meta.get(key) or {}).get("value", "")

                fetched[name] = {
                    "file_name": name,
                    "file_page": info[0].get("descriptionurl", ""),
                    "repository": (page or {}).get("imagerepository", ""),
                    "artist_html": field("Artist"),
                    "license": field("LicenseShortName"),
                    "license_url": field("LicenseUrl"),
                    "credit_html": field("Credit"),
                    "attribution_required": field("AttributionRequired"),
                    "restrictions": field("Restrictions"),
                    "copyrighted": field("Copyrighted"),
                    "width": info[0].get("width", 0),
                    "height": info[0].get("height", 0),
                    # A render at the width the website wants, which the API
                    # clamps to the original when the original is smaller.
                    "thumb_url": info[0].get("thumburl", ""),
                    "thumb_width": info[0].get("thumbwidth", 0),
                    "thumb_height": info[0].get("thumbheight", 0),
                }

        if fetched:
            with self._lock:
                self._meta.update(fetched)
                try:
                    META_CACHE.write_text(json.dumps(self._meta, indent=1))
                except OSError:
                    pass

        with self._lock:
            return {t: dict(self._meta[n]) for t, n in wanted.items()
                    if n in self._meta}


# --------------------------------------------------------------------------
# Round loading, off the UI thread
# --------------------------------------------------------------------------

class RoundLoader(threading.Thread):
    """
    Loads photos for the whole game in the background.

    Each round is a slot. A slot is filled by the next species from the plan;
    if that photo will not load, the slot quietly falls back to a spare, so a
    dead link never becomes a dead round.
    """

    def __init__(self, library, plan, spares, out_queue):
        super().__init__(daemon=True)
        self.library = library
        self.plan = plan
        self.spares = list(spares)
        self.out = out_queue

    def run(self):
        # Resolve every URL we might need in one or two API calls, so the
        # per-round work is a plain image download or a cache hit.
        try:
            self.library.resolve_many(
                [s["title"] for s in self.plan + self.spares])
        except Exception:
            pass  # fall back to resolving lazily, per species, below

        for index, species in enumerate(self.plan):
            candidates = [species]
            # Prefer a spare from the same side so the dog/cat balance holds.
            candidates += [s for s in self.spares if s["side"] == species["side"]]
            loaded = False
            for candidate in candidates:
                try:
                    image, credit = self.library.fetch(candidate["title"])
                except Exception:
                    continue
                if candidate in self.spares:
                    self.spares.remove(candidate)
                self.out.put((index, candidate, image, credit, None))
                loaded = True
                break
            if not loaded:
                self.out.put((index, species, None, None, "could not load a photo"))


# --------------------------------------------------------------------------
# Look and feel
# --------------------------------------------------------------------------

BG = "#12151c"
PANEL = "#1a1f2b"
INK = "#eef1f7"
MUTED = "#8792a8"
DOG_COLOR = "#e0913a"
DOG_SHADOW = "#3a2f18"
CAT_COLOR = "#7f7ae0"
CAT_SHADOW = "#231f4a"
GOOD = "#54c98a"
BAD = "#e8636b"
START_GREEN = "#2f8f5b"
START_SHADOW = "#163e2a"

IMAGE_BOX = (660, 440)


def lighten(colour, amount):
    """Mix a #rrggbb colour towards white, for hover states."""
    channels = (int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16))
    return "#%02x%02x%02x" % tuple(
        min(255, int(c + (255 - c) * amount)) for c in channels)


class ChoiceButton:
    """
    A two-line answer button.

    Built from a frame and labels rather than a tk.Button so that the entire
    panel is the click target: the padding and the subtitle line respond just
    like the big word does.
    """

    def __init__(self, parent, font, label, subtitle, colour, shadow, command,
                 size=20, sub_size=10, pad=46, pad_y=12):
        self.colour = colour
        self.hover = lighten(colour, 0.15)
        self.command = command
        self.enabled = True

        self.frame = tk.Frame(parent, bg=colour, cursor="hand2",
                              highlightthickness=0)
        self.title = tk.Label(self.frame, text=label, bg=colour, fg="#14161c",
                              font=(font, size, "bold"), cursor="hand2")
        self.title.pack(fill="x", padx=pad,
                        pady=(pad_y, 0 if subtitle else pad_y))

        self.subtitle = None
        if subtitle:
            self.subtitle = tk.Label(self.frame, text=subtitle, bg=colour,
                                     fg=shadow, font=(font, sub_size,
                                                      "italic"),
                                     cursor="hand2")
            self.subtitle.pack(fill="x", padx=pad, pady=(0, pad_y))

        for widget in self._parts():
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _parts(self):
        if self.subtitle is None:
            return (self.frame, self.title)
        return (self.frame, self.title, self.subtitle)

    def _paint(self, colour):
        for widget in self._parts():
            widget.config(bg=colour)

    def _on_click(self, _event):
        if self.enabled:
            self.command()

    def _on_enter(self, _event):
        if self.enabled:
            self._paint(self.hover)

    def _on_leave(self, _event):
        self._paint(self.colour)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._paint(self.colour)
        for widget in self._parts():
            widget.config(cursor="hand2" if enabled else "")

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)


def pick_font():
    """
    Pick the nicest proportional family this Tk can actually see.

    Tk built without Xft only exposes the core X11 fonts, where the usual
    names silently resolve to a monospace bitmap. Bitstream Charter is the
    one proportional face in that set, so it is the last stop before giving
    up and taking whatever the default is.
    """
    available = {name.lower(): name for name in tkfont.families()}
    for family in ("DejaVu Sans", "Noto Sans", "Liberation Sans", "Ubuntu",
                   "Segoe UI", "Helvetica Neue", "Bitstream Charter"):
        match = available.get(family.lower())
        if match:
            return match
    return "TkDefaultFont"


class DogOrCat:
    def __init__(self, root):
        self.root = root
        self.font = pick_font()
        self.library = PhotoLibrary()

        root.title("Dog or Cat?")
        root.configure(bg=BG)
        root.geometry("780x830")
        root.minsize(700, 760)

        self.photo = None          # keeps the current PhotoImage alive
        self.rounds = {}           # index -> (species, image, credit, error)
        self.queue = queue.Queue()
        self.index = 0
        self.score = 0
        self.streak = 0
        self.best_streak = 0
        self.answered = False
        self.missed = []
        self.playing = False       # False while the start page is up

        self._build_ui()
        self._bind_keys()
        # Dealt and downloading already, so the first photo is usually
        # waiting by the time the start page has been read.
        self.new_game()
        self.show_start()
        self.root.after(60, self._drain_queue)

    # -- construction ------------------------------------------------------
    def _build_ui(self):
        # Everything below lives in one frame so the start page can take the
        # window over without disturbing the game's own layout.
        self.game = tk.Frame(self.root, bg=BG)

        header = tk.Frame(self.game, bg=BG)
        header.pack(fill="x", padx=24, pady=(18, 6))

        tk.Label(header, text="Dog or Cat?", bg=BG, fg=INK,
                 font=(self.font, 22, "bold")).pack(side="left")

        self.stats = tk.Label(header, text="", bg=BG, fg=MUTED,
                              font=(self.font, 12))
        self.stats.pack(side="right")

        self.subtitle = tk.Label(
            self.game,
            text="Caniformia or Feliformia — which branch of Carnivora?",
            bg=BG, fg=MUTED, font=(self.font, 12))
        self.subtitle.pack(padx=24, anchor="w")

        frame = tk.Frame(self.game, bg=PANEL, width=IMAGE_BOX[0],
                         height=IMAGE_BOX[1])
        frame.pack(pady=14)
        frame.pack_propagate(False)
        self.image_label = tk.Label(frame, bg=PANEL, fg=MUTED,
                                    font=(self.font, 13))
        self.image_label.pack(expand=True)

        self.credit = tk.Label(self.game, text="", bg=BG, fg="#5b6479",
                               font=(self.font, 8))
        self.credit.pack()

        # Fixed-height bottom area so nothing jumps when the reveal appears.
        self.bottom = tk.Frame(self.game, bg=BG, height=230)
        self.bottom.pack(fill="x", padx=24, pady=(10, 18))
        self.bottom.pack_propagate(False)

        self._build_choices()
        self._build_reveal()
        self._build_start()

    def _build_choices(self):
        self.choices = tk.Frame(self.bottom, bg=BG)

        row = tk.Frame(self.choices, bg=BG)
        row.pack(pady=(24, 8))

        # Deliberately no emoji here: Tk 8.6 renders non-BMP characters
        # unreliably on Linux, and a tofu box in the main button is worse
        # than no picture at all.
        self.dog_button = ChoiceButton(
            row, self.font, "DOG", "Caniformia — dog-like",
            DOG_COLOR, DOG_SHADOW, lambda: self.answer(DOG))
        self.dog_button.pack(side="left", padx=10)

        self.cat_button = ChoiceButton(
            row, self.font, "CAT", "Feliformia — cat-like",
            CAT_COLOR, CAT_SHADOW, lambda: self.answer(CAT))
        self.cat_button.pack(side="left", padx=10)

        tk.Label(self.choices, text="keys:  ← or D for dog   •   "
                                    "→ or C for cat",
                 bg=BG, fg="#5b6479", font=(self.font, 9)).pack(pady=(14, 0))

    def _build_reveal(self):
        self.reveal = tk.Frame(self.bottom, bg=BG)

        self.verdict = tk.Label(self.reveal, text="", bg=BG, fg=INK,
                                font=(self.font, 17, "bold"))
        self.taxon = tk.Label(self.reveal, text="", bg=BG, fg=MUTED,
                              font=(self.font, 12))
        self.fact = tk.Label(self.reveal, text="", bg=BG, fg=INK,
                             font=(self.font, 12), wraplength=700,
                             justify="left")

        # Kept together so the results screen can hide them and the next
        # round can restore them with the same spacing.
        self.reveal_rows = [
            (self.verdict, {"anchor": "w"}),
            (self.taxon, {"anchor": "w", "pady": (2, 8)}),
            (self.fact, {"anchor": "w"}),
        ]
        for widget, options in self.reveal_rows:
            widget.pack(**options)

        self.next_button = tk.Button(
            self.reveal, text="Next  →", command=self.next_round,
            bg="#2b3346", fg=INK, activebackground="#39435c",
            activeforeground=INK, font=(self.font, 13, "bold"), relief="flat",
            bd=0, padx=22, pady=8, cursor="hand2", highlightthickness=0)
        self.next_button.pack(anchor="w", pady=(16, 0))

    def _build_start(self):
        self.start = tk.Frame(self.root, bg=BG)

        page = tk.Frame(self.start, bg=BG)
        page.pack(expand=True, padx=40)

        tk.Label(page, text="Dog or Cat?", bg=BG, fg=INK,
                 font=(self.font, 24, "bold")).pack(pady=(0, 4))
        tk.Label(page, text="Caniformia or Feliformia — "
                            "which branch of Carnivora?",
                 bg=BG, fg=MUTED, font=(self.font, 12)).pack(pady=(0, 22))

        blurb = (
            "The order Carnivora split in two roughly 50 million years ago, "
            "long before anything that looked like a "
            "dog or a cat existed. Every carnivoran alive sits on one side "
            "of that split, and the two sides are far wider than their "
            "nicknames suggest."
        )
        tk.Label(page, text=blurb, bg=BG, fg=INK, font=(self.font, 12),
                 wraplength=600, justify="left").pack(anchor="w")

        
        ChoiceButton(page, self.font, "START", "",
                     START_GREEN, START_SHADOW, self.start_game,
                     size=22, pad=72, pad_y=16).pack(pady=(20, 0))

        tk.Label(page, text="or press space", bg=BG, fg="#5b6479",
                 font=(self.font, 9)).pack(pady=(10, 0))

    def _branch_card(self, parent, title, subtitle, examples, colour):
        card = tk.Frame(parent, bg=PANEL)
        tk.Label(card, text=title, bg=PANEL, fg=colour,
                 font=(self.font, 14, "bold")).pack(padx=20, pady=(12, 0))
        tk.Label(card, text=subtitle, bg=PANEL, fg=MUTED,
                 font=(self.font, 10, "italic")).pack(padx=20)
        tk.Label(card, text=examples, bg=PANEL, fg=INK, justify="center",
                 font=(self.font, 11)).pack(padx=20, pady=(8, 14))
        return card

    # -- screens -----------------------------------------------------------
    def show_start(self):
        self.playing = False
        self.game.pack_forget()
        self.start.pack(fill="both", expand=True)

    def start_game(self):
        if self.playing:
            return
        self.playing = True
        self.start.pack_forget()
        self.game.pack(fill="both", expand=True)
        self.show_round()

    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self.answer(DOG))
        self.root.bind("<Right>", lambda e: self.answer(CAT))
        self.root.bind("d", lambda e: self.answer(DOG))
        self.root.bind("c", lambda e: self.answer(CAT))
        self.root.bind("<space>", lambda e: self._advance_key())
        self.root.bind("<Return>", lambda e: self._advance_key())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def _advance_key(self):
        if not self.playing:
            self.start_game()
        elif self.answered:
            self.next_round()

    # -- game flow ---------------------------------------------------------
    def new_game(self):
        dogs = [s for s in SPECIES if s["side"] == DOG]
        cats = [s for s in SPECIES if s["side"] == CAT]
        random.shuffle(dogs)
        random.shuffle(cats)

        half = ROUNDS // 2
        plan = dogs[:half] + cats[:ROUNDS - half]
        random.shuffle(plan)
        spares = dogs[half:] + cats[ROUNDS - half:]

        self.rounds = {}
        self.queue = queue.Queue()
        self.index = 0
        self.score = 0
        self.streak = 0
        self.best_streak = 0
        self.missed = []

        RoundLoader(self.library, plan, spares, self.queue).start()
        self.show_round()

    def _drain_queue(self):
        try:
            while True:
                index, species, image, credit, error = self.queue.get_nowait()
                self.rounds[index] = (species, image, credit, error)
                if index == self.index and not self.answered:
                    self.show_round()
        except queue.Empty:
            pass
        self.root.after(80, self._drain_queue)

    def show_round(self):
        self.answered = False
        self.reveal.pack_forget()
        self.subtitle.config(
            text="Caniformia or Feliformia — which branch of Carnivora?")
        self._update_stats()

        entry = self.rounds.get(self.index)
        if entry is None:
            self.image_label.config(image="", text="Fetching a photo…")
            self.photo = None
            self.credit.config(text=" ")
            self.choices.pack_forget()
            return

        species, image, credit, error = entry
        if error:
            self.image_label.config(image="", text="No photo available.\n"
                                                   "Check your connection.")
            self.photo = None
            self.credit.config(text=" ")
            self.choices.pack_forget()
            return

        self.photo = ImageTk.PhotoImage(self._fit(image))
        self.image_label.config(image=self.photo, text="")
        # The filename usually contains the species name, so the credit stays
        # hidden until the guess is in. A blank keeps the row's height, so
        # revealing it does not shift the layout.
        self.credit.config(text=" ")
        self.choices.pack(fill="both", expand=True)
        self._set_choices_enabled(True)

    @staticmethod
    def _fit(image):
        box_w, box_h = IMAGE_BOX[0] - 20, IMAGE_BOX[1] - 20
        scale = min(box_w / image.width, box_h / image.height)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        return image.resize(size, Image.Resampling.LANCZOS)

    def _set_choices_enabled(self, enabled):
        self.dog_button.set_enabled(enabled)
        self.cat_button.set_enabled(enabled)

    def answer(self, choice):
        if self.answered or not self.playing:
            return
        entry = self.rounds.get(self.index)
        if entry is None or entry[3]:
            return

        species, _, credit, _ = entry
        correct = choice == species["side"]
        self.answered = True
        self._set_choices_enabled(False)
        self.credit.config(text=credit)  # safe to name the file now

        if correct:
            self.score += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.streak = 0
            self.missed.append(species)

        side_word = "dog-like" if species["side"] == DOG else "cat-like"
        suborder = "Caniformia" if species["side"] == DOG else "Feliformia"

        if correct:
            headline = "Correct — " + species["name"]
            colour = GOOD
        else:
            headline = "Nope — " + species["name"]
            colour = BAD

        self.verdict.config(text=headline, fg=colour)
        self.taxon.config(
            text="%s → %s  (%s)" % (suborder, species["family"], side_word))
        self.fact.config(text=species["fact"])
        self.next_button.config(
            text="See results" if self.index + 1 >= ROUNDS else "Next  →")

        self.choices.pack_forget()
        for widget, options in self.reveal_rows:
            if not widget.winfo_manager():  # hidden by the results screen
                widget.pack(before=self.next_button, **options)
        self.reveal.pack(fill="both", expand=True, pady=(6, 0))
        self._update_stats()

    def next_round(self):
        if self.index + 1 >= ROUNDS:
            self.show_results()
        else:
            self.index += 1
            self.show_round()

    def _update_stats(self):
        shown = min(self.index + 1, ROUNDS)
        streak = ("   •   streak %d" % self.streak) if self.streak > 1 else ""
        self.stats.config(text="Round %d/%d   •   score %d%s"
                               % (shown, ROUNDS, self.score, streak))

    # -- results -----------------------------------------------------------
    def show_results(self):
        self.answered = True
        self.reveal.pack_forget()
        self.choices.pack_forget()
        self.photo = None
        self.image_label.config(image="", text="")
        self.credit.config(text="")

        pct = round(100 * self.score / ROUNDS)
        if pct == 100:
            remark = "Flawless. You know your carnivorans."
        elif pct >= 80:
            remark = "Strong. The pinnipeds did not fool you."
        elif pct >= 60:
            remark = "Respectable, given how many of these are traps."
        elif pct >= 40:
            remark = "The nicknames were working against you."
        else:
            remark = "In fairness, evolution designed these to confuse you."

        lines = ["%d / %d correct  (%d%%)" % (self.score, ROUNDS, pct),
                 "Best streak: %d" % self.best_streak, "", remark]
        if self.missed:
            lines += ["", "Worth a second look:"]
            for species in self.missed:
                suborder = ("Caniformia" if species["side"] == DOG
                            else "Feliformia")
                lines.append("   %s  —  %s, %s"
                             % (species["name"], suborder, species["family"]))

        self.image_label.config(text="\n".join(lines), fg=INK,
                                font=(self.font, 13), justify="left")
        self.subtitle.config(text="Game over")
        self.stats.config(text="")

        # Hide the per-round labels so "Play again" sits under the summary
        # instead of below a stack of empty rows.
        for widget, _ in self.reveal_rows:
            widget.pack_forget()
        self.next_button.config(text="Play again", command=self._replay)
        self.reveal.pack(fill="both", expand=True)

    def _replay(self):
        self.next_button.config(command=self.next_round)
        self.image_label.config(justify="center")
        self.new_game()


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def check_all():
    """Verify every species resolves to a downloadable photo."""
    library = PhotoLibrary()
    library.resolve_many([s["title"] for s in SPECIES])
    failures = []
    for i, species in enumerate(SPECIES, 1):
        try:
            image, _ = library.fetch(species["title"])
            status = "ok  %dx%d" % (image.width, image.height)
        except Exception as exc:
            status = "FAIL  %s" % exc
            failures.append(species["title"])
        print("%3d/%d  %-24s %-22s %s"
              % (i, len(SPECIES), species["name"], species["family"], status))

    dogs = sum(1 for s in SPECIES if s["side"] == DOG)
    print("\n%d species: %d Caniformia, %d Feliformia, %d tricky"
          % (len(SPECIES), dogs, len(SPECIES) - dogs,
             sum(1 for s in SPECIES if s["tricky"])))
    if failures:
        print("failed: " + ", ".join(failures))
        return 1
    print("all photos resolve")
    return 0


def main():
    if "--check" in sys.argv:
        return check_all()
    root = tk.Tk()
    DogOrCat(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
