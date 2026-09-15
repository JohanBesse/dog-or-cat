// The share card. Squares only, never the animals -- a spoiler in the paste
// would defeat the point of sharing the link.

export function shareText(state) {
  const grid = state.results.map(ok => (ok ? '🟩' : '🟥')).join('');
  return [
    `Dog or Cat? ${state.score}/${state.rounds}`,
    grid,
    `best streak ${state.bestStreak} · dogorcat.net`,
  ].join('\n');
}

export async function shareResult(text) {
  if (navigator.share) {
    try {
      await navigator.share({ text });
      return false;            // the sheet says what happened; we need not
    } catch (err) {
      if (err && err.name === 'AbortError') return false;
    }
  }
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    const box = document.createElement('textarea');
    box.value = text;
    box.setAttribute('readonly', '');
    box.style.position = 'fixed';
    box.style.opacity = '0';
    document.body.append(box);
    box.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    box.remove();
    return ok;
  }
}
