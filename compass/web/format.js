export const RIASEC = [
  "realistic",
  "investigative",
  "artistic",
  "social",
  "enterprising",
  "conventional",
];
export const LETTER = { realistic: "R", investigative: "I", artistic: "A", social: "S", enterprising: "E", conventional: "C" };
export const DIM_LABEL = {
  realistic: "Realistic",
  investigative: "Investigative",
  artistic: "Artistic",
  social: "Social",
  enterprising: "Enterprising",
  conventional: "Conventional",
};

// CSS custom property per interest, defined in style.css.
export const DIM_VAR = {
  realistic: "var(--R)",
  investigative: "var(--I)",
  artistic: "var(--A)",
  social: "var(--S)",
  enterprising: "var(--E)",
  conventional: "var(--C)",
};
export const LETTER_VAR = { R: "var(--R)", I: "var(--I)", A: "var(--A)", S: "var(--S)", E: "var(--E)", C: "var(--C)" };

/** Colour for a major's dominant interest, from its high-point code. */
export function stripeFor(code) {
  return LETTER_VAR[code && code[0]] || "var(--C)";
}

/** Tiny hyperscript helper. */
export function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

const KEY = "compass.answers.v1";

export function saveAnswers(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch (_) {
    /* private mode */
  }
}

export function loadAnswers() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

export function clearAnswers() {
  try {
    localStorage.removeItem(KEY);
  } catch (_) {
    /* ignore */
  }
}
