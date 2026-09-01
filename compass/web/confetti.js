// A small canvas confetti burst. No dependency, ~2s, cleans itself up.
import { DIM_VAR } from "./format.js";

const COLORS = Object.values(DIM_VAR).concat(["var(--accent)", "var(--accent-2)"]);

export function celebrate() {
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const canvas = document.createElement("canvas");
  canvas.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:50";
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const W = (canvas.width = innerWidth * dpr);
  const H = (canvas.height = innerHeight * dpr);
  canvas.style.width = innerWidth + "px";
  canvas.style.height = innerHeight + "px";
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  // resolve the CSS variables to real colours once
  const probe = document.createElement("span");
  document.body.appendChild(probe);
  const palette = COLORS.map((c) => {
    probe.style.color = c;
    return getComputedStyle(probe).color;
  });
  probe.remove();

  const N = 130;
  const bits = Array.from({ length: N }, () => ({
    x: W / 2 + (Math.random() - 0.5) * 120 * dpr,
    y: H * 0.28,
    vx: (Math.random() - 0.5) * 16 * dpr,
    vy: (Math.random() * -14 - 4) * dpr,
    g: 0.35 * dpr,
    size: (4 + Math.random() * 5) * dpr,
    rot: Math.random() * Math.PI,
    vr: (Math.random() - 0.5) * 0.3,
    color: palette[(Math.random() * palette.length) | 0],
    life: 1,
  }));

  const start = performance.now();
  function frame(now) {
    const t = now - start;
    ctx.clearRect(0, 0, W, H);
    for (const b of bits) {
      b.vy += b.g;
      b.x += b.vx;
      b.y += b.vy;
      b.vx *= 0.99;
      b.rot += b.vr;
      b.life = Math.max(0, 1 - t / 1900);
      ctx.save();
      ctx.globalAlpha = b.life;
      ctx.translate(b.x, b.y);
      ctx.rotate(b.rot);
      ctx.fillStyle = b.color;
      ctx.fillRect(-b.size / 2, -b.size / 2, b.size, b.size * 0.6);
      ctx.restore();
    }
    if (t < 2000) requestAnimationFrame(frame);
    else canvas.remove();
  }
  requestAnimationFrame(frame);
}
