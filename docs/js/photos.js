// Photo loading. A round must never show an empty box, so images are decoded
// before they are handed over, and the next rounds are fetched ahead of time.

const cache = new Map();   // url -> Promise<HTMLImageElement>

// One width for the whole session, chosen from the screen. Simpler than a
// srcset here, because the game preloads specific files.
export function pickWidth(widths, viewport = window.innerWidth,
                          dpr = window.devicePixelRatio || 1) {
  const wanted = Math.min(viewport, 660) * Math.min(dpr, 2);
  const sorted = widths.slice().sort((a, b) => a - b);
  return sorted.find(w => w >= wanted) ?? sorted[sorted.length - 1];
}

export function srcFor(species, width) {
  const photo = species.photo;
  const available = photo.widths.slice().sort((a, b) => a - b);
  const w = available.find(x => x >= width) ?? available[available.length - 1];
  return `${photo.stem}-${w}.${photo.formats[0]}`;
}

export function load(src) {
  if (cache.has(src)) return cache.get(src);
  const p = new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => {
      const done = () => resolve(img);
      if (!img.decode) return done();
      // Decoding first means the photo paints in the same frame it appears,
      // with no flash of empty box. It is only ever an optimisation, so a
      // decode that stalls must not strand the round: whichever settles
      // first wins.
      Promise.race([img.decode(), new Promise(r => setTimeout(r, 250))])
        .then(done, done);
    };
    img.onerror = () => reject(new Error('could not load ' + src));
    img.src = src;
  });
  cache.set(src, p);
  return p;
}

// Fill one slot, falling back to a spare of the same side if the photo is
// missing -- the browser-side version of RoundLoader.run().
export async function ensure(state, i, width) {
  const slot = state.plan[i];
  if (!slot || slot.status !== 'pending') return slot;
  slot.status = 'loading';

  const sameSide = state.spares.filter(s => s.side === slot.species.side);
  for (const candidate of [slot.species, ...sameSide]) {
    try {
      const img = await load(srcFor(candidate, width));
      const spare = state.spares.indexOf(candidate);
      if (spare !== -1) state.spares.splice(spare, 1);
      slot.species = candidate;
      slot.src = img.src;
      slot.status = 'ready';
      return slot;
    } catch (err) {
      /* try the next candidate */
    }
  }
  slot.status = 'failed';
  return slot;
}
