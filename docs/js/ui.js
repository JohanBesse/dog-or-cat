// Everything that touches the DOM. Screens are swapped with [hidden]; the
// species behind the current photo is never written into the document until
// the guess is in.

import * as game from './game.js';
import { ensure, pickWidth, srcFor } from './photos.js';
import { shareText, shareResult } from './share.js';

const $ = id => document.getElementById(id);
const el = {
  screens: () => document.querySelectorAll('.screen'),
  round: $('hud-round'), score: $('hud-score'), streak: $('hud-streak'),
  stage: $('stage'), photo: $('photo'), stageMsg: $('stage-msg'),
  credit: $('credit'), creditText: $('credit-text'),
  choices: $('panel-choices'), reveal: $('panel-reveal'),
  dog: $('btn-dog'), cat: $('btn-cat'),
  verdict: $('verdict'), taxon: $('taxon'), fact: $('fact'), next: $('next'),
  scoreLine: $('score-line'), bestStreak: $('best-streak'), remark: $('remark'),
  missedBlock: $('missed-block'), missed: $('missed'),
  shareSaid: $('share-said'),
};

let state = null;
let width = 660;
let allSpecies = [];      // every species, never narrowed
let rounds = 10;
const seen = new Set();   // ids shown recently, so replays vary

// ------------------------------------------------------------- screens

function show(name) {
  for (const section of el.screens()) {
    section.hidden = section.id !== `screen-${name}`;
  }
  state.screen = name;
  $(`screen-${name}`).focus();
}

// ------------------------------------------------------------- rounds

function renderHud() {
  const h = game.hud(state);
  el.round.textContent = h.round;
  el.score.textContent = h.score;
  el.streak.textContent = h.streak || '';
  el.streak.hidden = !h.streak;
}

function setChoicesEnabled(on) {
  el.dog.disabled = !on;
  el.cat.disabled = !on;
}

function renderRound() {
  state.answered = false;
  el.reveal.hidden = true;
  el.choices.hidden = false;
  el.credit.classList.remove('shown');
  el.creditText.replaceChildren();
  renderHud();

  const slot = state.plan[state.index];
  if (!slot || slot.status === 'failed') {
    el.photo.hidden = true;
    el.stage.classList.remove('loading');
    el.stageMsg.hidden = false;
    el.stageMsg.textContent = slot
      ? 'No photo available for this one.'
      : 'Fetching a photo…';
    setChoicesEnabled(false);
    return;
  }
  if (slot.status !== 'ready') {
    el.photo.hidden = true;
    el.stage.classList.add('loading');
    el.stageMsg.hidden = false;
    el.stageMsg.textContent = 'Fetching a photo…';
    setChoicesEnabled(false);
    return;
  }

  el.stage.classList.remove('loading');
  el.stageMsg.hidden = true;
  el.photo.hidden = false;
  el.photo.src = slot.src;
  // Deliberately says nothing about the animal: the alt text would otherwise
  // hand the answer to anyone reading the page with a screen reader.
  el.photo.alt = `Photograph of a carnivoran — round ${state.index + 1} of ${state.rounds}.`;
  setChoicesEnabled(true);
}

async function fill(i) {
  if (i >= state.plan.length) return;
  const before = state.plan[i] && state.plan[i].status;
  if (before !== 'pending') return;
  await ensure(state, i, width);
  if (i === state.index && !state.answered && state.screen === 'play') {
    renderRound();
  }
}

function prefetch() {
  fill(state.index + 1);
  fill(state.index + 2);
}

// ------------------------------------------------------------- reveal

function guess(side) {
  if (state.screen !== 'play') return;
  const result = game.answer(state, side);
  if (!result) return;

  setChoicesEnabled(false);
  const species = result.species;
  const credit = species.credit;

  el.verdict.textContent = result.headline;
  el.verdict.className = 'verdict ' + (result.correct ? 'correct' : 'wrong');
  el.taxon.textContent = result.taxon;
  el.fact.textContent = species.fact;
  el.next.textContent = state.index + 1 >= state.rounds ? 'See results' : 'Next →';

  // Safe to name the file now that the guess is locked in.
  const parts = [document.createTextNode(`Photo: ${credit.artist} · `)];
  if (credit.license_url) {
    const a = document.createElement('a');
    a.href = credit.license_url;
    a.rel = 'license';
    a.textContent = credit.license;
    parts.push(a);
  } else {
    parts.push(document.createTextNode(credit.license));
  }
  parts.push(document.createTextNode(' · '));
  const source = document.createElement('a');
  source.href = credit.file_page;
  source.textContent = 'Wikimedia Commons';
  parts.push(source);
  el.creditText.replaceChildren(...parts);
  el.credit.classList.add('shown');

  el.photo.alt = `Photograph of a ${species.name}.`;
  el.choices.hidden = true;
  el.reveal.hidden = false;
  renderHud();
  el.next.focus();
  prefetch();
}

function advance() {
  if (state.screen === 'start') return startGame();
  if (state.screen !== 'play' || !state.answered) return;
  if (state.index + 1 >= state.rounds) return showResults();
  state.index += 1;
  renderRound();
  fill(state.index);
  prefetch();
}

// ------------------------------------------------------------- results

const LAST_GAME = 'dogorcat:last-game';

function rememberPlayed() {
  // The credits page lists only the photographs you have been shown, so it
  // needs to know which ones those were. Private browsing can refuse this,
  // and the page copes with an empty list.
  try {
    const ids = state.plan.slice(0, state.results.length).map(s => s.species.id);
    localStorage.setItem(LAST_GAME, JSON.stringify(ids));
  } catch (err) { /* no storage, no credits list */ }
}

function showResults() {
  rememberPlayed();
  const pct = game.percent(state);
  el.scoreLine.textContent = `${state.score} / ${state.rounds} correct  (${pct}%)`;
  el.bestStreak.textContent = `Best streak: ${state.bestStreak}`;
  el.remark.textContent = game.remark(pct);

  el.missed.replaceChildren();
  el.missedBlock.hidden = state.missed.length === 0;
  for (const species of state.missed) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = species.wiki;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = species.name;
    const tail = document.createElement('span');
    tail.className = 'taxon-inline';
    tail.textContent = ` — ${game.suborder(species)}, ${species.family}`;
    li.append(a, tail);
    el.missed.append(li);
  }
  el.shareSaid.hidden = true;
  show('results');
}

// ------------------------------------------------------------- game flow

// Deal a new game. Replays are biased away from the animals recently shown,
// but the pool they are drawn from is always the full list: narrowing the
// list itself would leave it too small to deal five and five.
function freshState() {
  const half = Math.ceil(rounds / 2);
  const unseenOn = side =>
    allSpecies.filter(s => s.side === side && !seen.has(s.id)).length;
  if (unseenOn('dog') < half || unseenOn('cat') < half) seen.clear();

  const next = game.newState(allSpecies.filter(s => !seen.has(s.id)), rounds);
  for (const slot of next.plan) seen.add(slot.species.id);
  return next;
}

function startGame() {
  // START on a finished game deals a new one rather than resuming the last
  // round of the old one.
  if (state.results.length >= rounds) state = freshState();
  state.screen = 'play';
  show('play');
  renderRound();
  fill(state.index);
  prefetch();
}

function newGame() {
  state = freshState();
  startGame();
}

// Leaving a game -- from the results screen or with Escape -- abandons it.
// Without a fresh deal here, START would drop the player back into the game
// they just walked away from.
function toStart() {
  state = freshState();
  show('start');
  fill(0);
  fill(1);
}

// ------------------------------------------------------------- events

const ACTIONS = {
  start: () => startGame(),
  dog: () => guess(game.DOG),
  cat: () => guess(game.CAT),
  next: () => advance(),
  again: () => newGame(),
  home: () => toStart(),
  share: async () => {
    const copied = await shareResult(shareText(state));
    el.shareSaid.hidden = !copied;
  },
};

document.addEventListener('click', event => {
  const target = event.target.closest('[data-action]');
  if (target) ACTIONS[target.dataset.action]?.();
});

document.addEventListener('keydown', event => {
  if (event.metaKey || event.ctrlKey || event.altKey || event.repeat) return;
  const onButton = event.target.closest && event.target.closest('button');
  switch (event.key) {
    case 'ArrowLeft': case 'd': case 'D': guess(game.DOG); break;
    case 'ArrowRight': case 'c': case 'C': guess(game.CAT); break;
    case ' ': case 'Enter':
      if (onButton) return;            // let the focused button fire once
      event.preventDefault();
      advance();
      break;
    case 'Escape':
      if (state.screen !== 'start') toStart();
      break;
    default: return;
  }
});

// ------------------------------------------------------------- boot

async function boot() {
  const data = await fetch('data/species.json').then(r => r.json());
  allSpecies = data.species;
  rounds = data.rounds;
  width = pickWidth(data.species[0].photo.widths);
  state = freshState();
  // Deal and start downloading while the start page is still being read --
  // the same trick the desktop game plays.
  fill(0);
  fill(1);
  show('start');
  window.dogorcat = { state: () => state, game, srcFor };   // for the self-test
}

boot();
