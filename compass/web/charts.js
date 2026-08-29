// Hand-drawn RIASEC hexagon. Holland's model is literally a hexagon with the six
// types in R-I-A-S-E-C order, so the chart doubles as a picture of the theory.
import { RIASEC, LETTER } from "./format.js";

const SVGNS = "http://www.w3.org/2000/svg";

function el(name, attrs) {
  const n = document.createElementNS(SVGNS, name);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
}

function points(values, cx, cy, radius) {
  // values are 0..1; first axis points up, then clockwise
  return RIASEC.map((_, i) => {
    const angle = -Math.PI / 2 + (i * Math.PI) / 3;
    const r = radius * Math.max(0.04, values[i]);
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  });
}

const path = (pts) => pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ") + " Z";

/**
 * @param {object} opts
 * @param {number[]} [opts.user]   six values, already normalised 0..1
 * @param {number[]} [opts.major]  six values, already normalised 0..1
 * @param {number}   [opts.size]
 * @param {boolean}  [opts.animate]
 */
export function hexagon({ user, major, size = 220, animate = true } = {}) {
  const pad = 26;
  const radius = (size - pad * 2) / 2;
  const cx = size / 2;
  const cy = size / 2;

  const svg = el("svg", { class: "hex", viewBox: `0 0 ${size} ${size}`, width: size, height: size });

  // grid rings
  for (const frac of [0.25, 0.5, 0.75, 1]) {
    svg.appendChild(el("path", { class: "grid", d: path(points(RIASEC.map(() => frac), cx, cy, radius)) }));
  }
  // spokes + labels
  RIASEC.forEach((dim, i) => {
    const angle = -Math.PI / 2 + (i * Math.PI) / 3;
    const ex = cx + radius * Math.cos(angle);
    const ey = cy + radius * Math.sin(angle);
    svg.appendChild(el("line", { class: "grid", x1: cx, y1: cy, x2: ex, y2: ey }));
    const lx = cx + (radius + 12) * Math.cos(angle);
    const ly = cy + (radius + 12) * Math.sin(angle);
    const t = el("text", {
      x: lx,
      y: ly,
      "text-anchor": Math.abs(lx - cx) < 4 ? "middle" : lx > cx ? "start" : "end",
      "dominant-baseline": "middle",
    });
    t.textContent = LETTER[dim];
    svg.appendChild(t);
  });

  if (major) {
    svg.appendChild(el("path", { class: "major", d: path(points(major, cx, cy, radius)) }));
  }
  if (user) {
    const poly = el("path", { class: "user", d: path(points(user, cx, cy, radius)) });
    svg.appendChild(poly);
    if (animate) {
      poly.style.transformOrigin = "center";
      poly.animate(
        [
          { transform: "scale(0.2)", opacity: 0 },
          { transform: "scale(1)", opacity: 1 },
        ],
        { duration: 420, easing: "cubic-bezier(.2,.8,.2,1)" },
      );
    }
  }
  return svg;
}

/** Normalise a {dim: value} map given a scale max. */
export function norm(riasecMap, scaleMax) {
  return RIASEC.map((d) => Math.max(0, Math.min(1, (riasecMap[d] || 0) / scaleMax)));
}
