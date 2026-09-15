# Dog or Cat?

A guessing game about the two great branches of the order Carnivora:
**Caniformia**, the dog-like carnivorans, and **Feliformia**, the cat-like
ones. You get a photograph and one guess.

The catch is that these are suborders, not families, and they are much wider
than their nicknames suggest. Seals, bears, otters, raccoons and skunks are all
dog-like. Hyenas, mongooses, meerkats and civets are all cat-like. A game that
sounds like a coin flip is not one.

There are two ways to play it: a desktop version in tkinter, and a website.

## The desktop game

```bash
python3 dogorcat.py            # play
python3 dogorcat.py --check    # verify every species photo still resolves
```

Needs `requests` and `Pillow`. Photos are fetched from Wikipedia on demand and
cached in `~/.cache/dog-or-cat/`, so after the first game it works offline.

## The website

`docs/` is a static site, published by GitHub Pages at
[dogorcat.net](https://dogorcat.net). It has no backend: the game is three
small ES modules, and every photograph is bundled with the site rather than
hotlinked from Wikimedia.

`SPECIES` in `dogorcat.py` is the single source of truth for both versions.
`tools/build_web.py` reads it and generates the data half of `docs/`:

```bash
python3 tools/build_web.py                 # build (uses caches, no downloads)
python3 tools/build_web.py --refresh-meta   # re-read every licence from Commons
python3 tools/build_web.py --check-free     # verify licences and stop
```

| Generated | Hand-written |
|---|---|
| `docs/data/species.json` | `docs/index.html` |
| `docs/photos/*` | `docs/css/app.css` |
| `docs/credits.html` | `docs/js/*.js` |
| `docs/assets/og-card.png` | `docs/CNAME`, `docs/.nojekyll` |

`docs/CNAME` and `docs/.nojekyll` must stay committed. Without `CNAME` the
custom domain quietly detaches; without `.nojekyll` GitHub runs Jekyll over the
output and eats anything beginning with an underscore.

### Running it locally

```bash
python3 -m http.server 8000 -d docs     # then open localhost:8000
```

### Tests

```bash
python3 -m http.server 8000             # from the repo root
# open localhost:8000/tools/selftest.html
```

427 assertions covering the deal (always ten rounds, always five dog-like and
five cat-like), scoring and streaks, the remark thresholds, photo substitution
when an image fails, and that no species name leaks into a photo URL before the
guess.

### Why the photo filenames are hashes

`photos/8f3a91c2-660.webp`, not `photos/gray-wolf-660.webp`. The `src` is
visible in the DOM, on link hover and in devtools, so a readable filename would
give the answer away before the guess — the same reason the desktop game hides
its credit line until you have answered. Hashed names also make each URL
immutable, which is the only cache control GitHub Pages allows.

## Photographs

Every photograph comes from Wikimedia Commons and is used under its own
licence. 53 of the 59 require attribution, which is what `docs/credits.html`
is for. The build refuses to publish any image that is not clearly freely
licensed, so adding a species can fail the build rather than quietly shipping
something unlicensed.

A few species are pinned to a specific Commons file in `tools/overrides.py`,
because the photo Wikipedia leads with is too small to fill the layout.

## Deploying

Pages serves `master` + `/docs`. To publish a change:

```bash
python3 tools/build_web.py
git commit -am "Fix the maned wolf fact"
git push origin master
```

Photos are content-hashed, so an edit to a fact changes one line of
`species.json` and no images.

DNS for the apex, at whichever registrar holds dogorcat.net:

| Type | Host | Value |
|---|---|---|
| A | `@` | `185.199.108.153` `185.199.109.153` `185.199.110.153` `185.199.111.153` |
| AAAA | `@` | `2606:50c0:8000::153` `2606:50c0:8001::153` `2606:50c0:8002::153` `2606:50c0:8003::153` |
| CNAME | `www` | `johanbesse.github.io` |

Nothing else on the apex, and no CAA record that omits `letsencrypt.org` —
either will stop the certificate from issuing. If the domain is on Cloudflare,
every record must be **DNS only**, never proxied.
