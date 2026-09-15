// Pure game logic, ported from new_game()/answer()/show_results() in
// dogorcat.py. No DOM in here, so the rules can be checked on their own.

export const DOG = 'dog';
export const CAT = 'cat';

export function shuffle(list, rand = Math.random) {
  const out = list.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// Exactly five dog-like and five cat-like, in a shuffled order. The leftovers
// are spares, used only to stand in for a photo that will not load -- always
// from the same side, so the 5/5 balance survives the substitution.
export function deal(all, rounds, rand = Math.random) {
  const dogs = shuffle(all.filter(s => s.side === DOG), rand);
  const cats = shuffle(all.filter(s => s.side === CAT), rand);
  const half = Math.floor(rounds / 2);
  const plan = shuffle([...dogs.slice(0, half), ...cats.slice(0, rounds - half)], rand);
  return {
    plan: plan.map(species => ({ species, status: 'pending', src: null })),
    spares: [...dogs.slice(half), ...cats.slice(rounds - half)],
  };
}

export function newState(all, rounds, rand = Math.random) {
  const { plan, spares } = deal(all, rounds, rand);
  return {
    all, rounds, plan, spares,
    index: 0, score: 0, streak: 0, bestStreak: 0,
    answered: false, missed: [], results: [],
    screen: 'start',
  };
}

export const suborder = s => (s.side === DOG ? 'Caniformia' : 'Feliformia');
export const sideWord = s => (s.side === DOG ? 'dog-like' : 'cat-like');

export function answer(state, choice) {
  const slot = state.plan[state.index];
  if (state.answered || !slot || slot.status !== 'ready') return null;

  const species = slot.species;
  const correct = choice === species.side;
  state.answered = true;
  if (correct) {
    state.score += 1;
    state.streak += 1;
    state.bestStreak = Math.max(state.bestStreak, state.streak);
  } else {
    state.streak = 0;
    state.missed.push(species);
  }
  state.results.push(correct);

  return {
    correct,
    species,
    headline: `${correct ? 'Correct' : 'Nope'} — ${species.name}`,
    taxon: `${suborder(species)} → ${species.family}  (${sideWord(species)})`,
  };
}

export function hud(state) {
  const shown = Math.min(state.index + 1, state.rounds);
  return {
    round: `Round ${shown}/${state.rounds}`,
    score: `score ${state.score}`,
    // The desktop game only shows a streak once it is worth mentioning.
    streak: state.streak > 1 ? `streak ${state.streak}` : null,
  };
}

export function remark(pct) {
  if (pct === 100) return 'Flawless. You know your carnivorans.';
  if (pct >= 80) return 'Strong. The pinnipeds did not fool you.';
  if (pct >= 60) return 'Respectable, given how many of these are traps.';
  if (pct >= 40) return 'The nicknames were working against you.';
  return 'In fairness, evolution designed these to confuse you.';
}

export const percent = state => Math.round(100 * state.score / state.rounds);
