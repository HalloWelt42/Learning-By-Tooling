/**
 * gamification.js -- Zentrale Konstanten fuer alle Belohnungssysteme
 *
 * Single Source of Truth: Wenn hier Werte geaendert werden,
 * passt sich die gesamte App an (Guide, Progress, Learn, SessionBar).
 *
 * Backend-Spiegel: Die Schwellenwerte muessen mit backend/routes/sessions.py
 * uebereinstimmen. Bei Aenderungen BEIDE Stellen aktualisieren.
 */

// -- Guertelfarben (10 Farben, 3 Sterne pro Farbe = 30 Stufen) ---------------

export const BELT_COLORS = [
  { name: 'Weiß',    hex: '#aaaaaa' },
  { name: 'Gelb',    hex: '#f0c040' },
  { name: 'Grün',    hex: '#40b060' },
  { name: 'Blau',    hex: '#4080e0' },
  { name: 'Rot',     hex: '#e04040' },
  { name: 'Schwarz', hex: '#404040' },
  { name: 'Bronze',  hex: '#cd7f32' },
  { name: 'Silber',  hex: '#c0c0c0' },
  { name: 'Gold',    hex: '#ffd700' },
  { name: 'Platin',  hex: '#b0b8d0' },
]

export const STAR_COLORS = ['#cd7f32', '#c0c0c0', '#ffd700']  // Bronze, Silber, Gold

// -- Abzeichen (6 Typen, 30 Stufen) ------------------------------------------

export const ACHIEVEMENTS = [
  {
    id: 'sessions', name: 'Ausdauer', desc: 'Sessions absolviert', icon: 'fa-dumbbell',
    thresholds: [1,3,5,10,20,35,50,80,120,175,250,350,500,700,900,1100,1300,1500,1750,2000,2250,2500,2750,3000,3100,3200,3350,3400,3500,3650],
  },
  {
    id: 'correct', name: 'Wissenssammler', desc: 'Richtige Antworten', icon: 'fa-brain',
    thresholds: [5,15,30,60,120,250,500,800,1200,1800,2500,3500,5000,7000,9000,11000,14000,17000,20000,23000,25000,28000,31000,35000,38000,42000,46000,48000,49000,50000],
  },
  {
    id: 'streak', name: 'Serie', desc: 'Längste Korrekt-Serie', icon: 'fa-fire',
    thresholds: [3,5,7,10,12,15,18,20,25,30,35,40,45,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,195,200],
  },
  {
    id: 'cards', name: 'Entdecker', desc: 'Verschiedene Karten gesehen', icon: 'fa-compass',
    thresholds: [5,10,20,35,50,75,100,150,200,300,400,500,650,800,1000,1200,1500,1800,2000,2300,2600,2800,3100,3500,3800,4100,4500,4700,4900,5000],
  },
  {
    id: 'perfect', name: 'Makellos', desc: 'Perfekte Sessions (100%)', icon: 'fa-trophy',
    thresholds: [1,2,3,5,8,12,18,25,35,50,65,80,100,130,170,220,280,350,400,450,500,550,600,700,750,800,900,950,975,1000],
  },
  {
    id: 'days', name: 'Beständig', desc: 'Tage mit Lernaktivität', icon: 'fa-calendar-check',
    thresholds: [1,3,5,7,14,21,30,45,60,90,120,150,180,250,365,450,550,700,800,900,1000,1100,1200,1400,1500,1600,1700,1750,1800,1825],
  },
]

// -- XP-Regeln ----------------------------------------------------------------

export const XP_RULES = {
  // Basis-XP pro Ergebnis
  base: { correct: 10, wrong: 10, skip: 1 },
  // Testmodus: nur korrekte Antworten voll belohnt
  testBase: { correct: 10, wrong: 1, skip: 0 },

  // Modus-Typ: Lern- vs. Testmodus
  testModes: ['mc', 'write'],
  learnModes: ['standard', 'srs'],

  // Anti-Gaming: unter 3s = 0 XP
  minTimeMs: 3000,

  // Karten-Schwierigkeit
  cardDifficulty: { 1: 0.7, 2: 1.0, 3: 1.4 },
  cardDifficultyLabels: { 1: 'Leicht', 2: 'Mittel', 3: 'Schwer' },

  // Modusfaktor
  modeFactor: { standard: 1.0, srs: 1.2, mc: 1.3, write: 1.5 },
  modeLabels: { standard: 'Karteikarte', srs: 'Spaced Repetition', mc: 'Multiple Choice', write: 'Freitext' },

  // Fortschrittsfaktor (Intervall in Tagen)
  progressFactor: [
    { max: 1,  factor: 1.0, label: 'Neu / Heute' },
    { max: 7,  factor: 1.1, label: '2-7 Tage' },
    { max: 30, factor: 1.3, label: '8-30 Tage' },
    { max: 90, factor: 1.5, label: '31-90 Tage' },
    { max: Infinity, factor: 1.2, label: '> 90 Tage' },
  ],

  // Streak/Combo-Faktor
  streakMultBase: 1.0,
  streakMultPerStep: 0.05,
  streakMultMax: 2.0,

  // Speed-Bonus
  speedBonusXp: 5,
  speedBonusMinMs: 3000,
  speedBonusMaxMs: 5000,
}

// -- Waehrung (Muenzen) -------------------------------------------------------

export const COIN_TIERS = [
  { name: 'Diamant', value: 1000000, color: '#4FC3F7', shape: 'pentagon' },
  { name: 'Gold',    value: 1000,    color: '#FFD700', shape: 'circle' },
  { name: 'Silber',  value: 1,       color: '#C0C0C0', shape: 'circle' },
]

export function coinBreakdown(xpTotal) {
  let rest = xpTotal || 0
  return COIN_TIERS.map(t => {
    const count = Math.floor(rest / t.value)
    rest = rest % t.value
    return { ...t, count }
  })
}

// -- Completion-Bonus ---------------------------------------------------------

export const COMPLETION_BONUS = [
  { minCards: 20, maxWrong: 0, bonus: 20, label: '20+ Karten, 0 Fehler' },
  { minCards: 5,  maxWrong: Infinity, bonus: 1, label: '5+ Karten beantwortet' },
]

// -- Verdict-Texte (Result-Screen) --------------------------------------------

export const VERDICTS = [
  { min: 100, text: 'Makellos',      color: 'var(--ok)' },
  { min: 90,  text: 'Ausgezeichnet', color: 'var(--ok)' },
  { min: 80,  text: 'Sehr gut',      color: 'var(--ok)' },
  { min: 60,  text: 'Gut gemacht',   color: 'var(--accent)' },
  { min: 40,  text: 'Solide Basis',  color: 'var(--warn)' },
  { min: 0,   text: 'Weiter üben',   color: 'var(--err)' },
]

export function getVerdict(pct) {
  return VERDICTS.find(v => pct >= v.min) || VERDICTS[VERDICTS.length - 1]
}

// -- Combo-System (rein Frontend) ---------------------------------------------

export const COMBO = {
  minDisplay: 3,       // Ab 3er-Combo anzeigen
  milestones: [3, 5, 10, 15, 20],
}

// -- Hilfsfunktionen ----------------------------------------------------------

export function calcLevel(value, thresholds) {
  let level = 0
  for (const t of thresholds) {
    if (value >= t) level++
    else break
  }
  if (level === 0) {
    return {
      level: 0, stars: 0, colorIdx: 0, color: BELT_COLORS[0],
      starColors: [], nextAt: thresholds[0] || 0,
    }
  }
  const colorIdx = Math.min(Math.floor((level - 1) / 3), 9)
  const stars = ((level - 1) % 3) + 1
  const nextAt = level < thresholds.length ? thresholds[level] : null
  const starColors = STAR_COLORS.slice(0, stars)
  return { level, stars, colorIdx, color: BELT_COLORS[colorIdx], starColors, nextAt }
}
