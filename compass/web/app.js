import { api } from "./api.js";
import { hexagon, norm } from "./charts.js";
import { celebrate } from "./confetti.js";
import {
  h,
  clear,
  mount,
  RIASEC,
  DIM_LABEL,
  DIM_VAR,
  LETTER,
  LETTER_VAR,
  stripeFor,
  loadAnswers,
  saveAnswers,
  clearAnswers,
} from "./format.js";
import { runQuiz } from "./quiz.js";

const view = document.getElementById("view");
const CACHE = { questionnaire: null, majors: null, meta: null };

// ---------------------------------------------------------------- theme
const themeBtn = document.getElementById("theme-toggle");
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  try {
    localStorage.setItem("compass.theme", t);
  } catch (_) {
    /* ignore */
  }
}
themeBtn.addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  applyTheme(cur === "dark" ? "light" : "dark");
});
try {
  const saved = localStorage.getItem("compass.theme");
  if (saved) applyTheme(saved);
} catch (_) {
  /* ignore */
}

// ---------------------------------------------------------------- helpers
function spinner() {
  return mount(clear(view),h("div", { class: "spinner" }));
}

async function ensure(key, loader) {
  if (!CACHE[key]) CACHE[key] = await loader();
  return CACHE[key];
}

function teardownQuiz() {
  view.dispatchEvent(new Event("quiz:teardown"));
}

function hasAnswers() {
  const a = loadAnswers();
  return a && Object.keys(a.answers || {}).length >= 6;
}

/** Circular fit gauge as an SVG. */
function gauge(score, color = "var(--accent)") {
  const r = 56;
  const c = 2 * Math.PI * r;
  const svg = `
    <svg viewBox="0 0 132 132" width="132" height="132">
      <circle cx="66" cy="66" r="${r}" fill="none" stroke="var(--surface-2)" stroke-width="10"/>
      <circle cx="66" cy="66" r="${r}" fill="none" stroke="${color}" stroke-width="10"
        stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - score / 100)}"/>
    </svg>`;
  return h(
    "div",
    { class: "gauge" },
    Object.assign(document.createElement("div"), { innerHTML: svg }).firstElementChild,
    h("div", { class: "num" }, h("b", {}, String(score)), h("span", {}, "fit")),
  );
}

/** The three-letter interest code, each letter in its colour. */
function codeChip(code) {
  return h(
    "span",
    { class: "code-chip" },
    ...code.split("").map((L) => h("i", { style: `background:${LETTER_VAR[L] || "var(--C)"}` }, L)),
  );
}

// ---------------------------------------------------------------- landing
function landing() {
  const cta = h("div", { class: "cta" });
  if (hasAnswers()) {
    cta.append(
      h("button", { class: "primary", onclick: () => (location.hash = "#/results") }, "See my results"),
      h("button", { onclick: () => (location.hash = "#/quiz") }, "Retake the quiz"),
    );
  } else {
    cta.append(
      h("button", { class: "primary", onclick: () => (location.hash = "#/quiz") }, "Start the quiz"),
      h("button", { onclick: () => (location.hash = "#/sample") }, "See a sample result"),
    );
  }

  const strip = h(
    "div",
    { class: "riasec-strip" },
    ...RIASEC.map((d) =>
      h(
        "span",
        { class: "riasec-pill" },
        h("b", { style: `background:${DIM_VAR[d]}` }, LETTER[d]),
        DIM_LABEL[d],
      ),
    ),
  );

  const pillars = h(
    "div",
    { class: "pillars" },
    pillar("Real interest data", "Every major is profiled from O*NET, the interest database career counselors use, joined to the government's CIP-to-SOC crosswalk."),
    pillar("It shows its work", "Each recommendation names which of your answers drove it, and where you and the major do not line up."),
    pillar("Honest about limits", "Interest fit is one signal. It is not aptitude, and it is not a prediction of the job market."),
  );

  const meta = h(
    "div",
    { class: "hero-meta" },
    h("span", {}, "🎓 Built for high school students"),
    h("span", {}, "⏱ About 5 minutes"),
    h("span", {}, "🧭 112 majors, ranked and explained"),
  );

  mount(clear(view),
    h(
      "section",
      { class: "hero" },
      h("p", { class: "eyebrow" }, "Career Compass"),
      h("h1", {}, "Find your ", h("span", { class: "grad" }, "major")),
      h(
        "p",
        { class: "lede" },
        "Answer a short interest inventory. Get 112 college majors ranked for you, each with the reason it fits.",
      ),
      cta,
      meta,
      strip,
    ),
    pillars,
  );
}

const pillar = (title, body) =>
  h("div", { class: "card pillar" }, h("h3", {}, title), h("p", {}, body));

// ---------------------------------------------------------------- quiz
async function quizView() {
  spinner();
  const q = await ensure("questionnaire", api.questions);
  const saved = loadAnswers();
  teardownQuiz();
  clear(view);

  // The quiz always starts clean at 30. The one exception is the explicit
  // "answer the other 30" link on the results page, which sets `resume`.
  const n = saved ? Object.keys(saved.answers || {}).length : 0;
  const resuming = !!(saved && !saved.sample && saved.resume === true && n > 0 && n < 60);

  runQuiz(view, q, {
    answers: resuming ? { ...saved.answers } : {},
    onDone: (answers) => {
      saveAnswers({ answers, ts: Date.now(), completed: true, resume: false });
      location.hash = "#/results";
    },
  });
}

// ---------------------------------------------------------------- results
async function results() {
  const saved = loadAnswers();
  if (!saved || Object.keys(saved.answers || {}).length < 6) {
    location.hash = "#/quiz";
    return;
  }
  spinner();
  const meta = await ensure("meta", api.meta);
  const data = await api.score(saved.answers, saved.dealbreakers || [], 24);
  renderResults(data, meta, !!saved.sample);

  // Celebrate a real match, once, the first time these results are seen.
  const weak = data.results[0].score < 55 || data.confidence === "low";
  if (!weak && !saved.celebrated && !saved.sample) {
    saveAnswers({ ...saved, celebrated: true });
    setTimeout(celebrate, 150);
  }
}

function renderResults(data, meta, isSample) {
  const p = data.profile;
  const userHex = norm(p.riasec, 4);
  const [top, ...rest] = data.results;
  const topColor = stripeFor(top.major.high_point_code);
  const weak = top.score < 55 || data.confidence === "low";

  const matchHero = h(
    "div",
    { class: "match-hero" },
    gauge(top.score, weak ? "var(--ink-3)" : topColor),
    h(
      "div",
      {},
      h("div", { class: "label" }, weak ? "Closest fit" : "Your top match"),
      h("h2", {}, top.major.name),
      weak
        ? h(
            "p",
            {},
            "Nothing scored as a strong match. Your answers did not point clearly in one direction, so the ranking below is a loose guide. ",
            h("a", { href: "#/quiz" }, "Retake"),
            " and use the full range (some strong dislikes, some strong likes) for a sharper result.",
          )
        : h("p", {}, top.explanation ? top.explanation.summary : top.major.blurb),
      weak
        ? null
        : h(
            "div",
            { class: "why-tags" },
            ...(top.explanation ? top.explanation.matches : []).slice(0, 3).map((d) => h("span", { class: "tag pos" }, DIM_LABEL[d])),
            ...(top.explanation ? top.explanation.clashes : []).slice(0, 2).map((d) => h("span", { class: "tag neg" }, DIM_LABEL[d])),
          ),
      h("p", { class: "tiny", style: "margin-top:.7rem" }, h("a", { href: "#/major/" + top.major.slug }, "Full page for " + top.major.name + " →")),
    ),
  );

  const profileBar = h(
    "div",
    { class: "card profile-bar" },
    h(
      "div",
      {},
      h("h3", {}, "Your interest profile ", codeChip(p.high_point_code)),
      h(
        "p",
        { class: "tiny muted", style: "margin:.2rem 0 0" },
        `${p.answered} questions answered. `,
        h("span", { class: "conf " + data.confidence }, data.confidence + " confidence"),
        "  ·  ",
        h("a", { href: "#/quiz" }, "Retake"),
        "  ·  ",
        h(
          "a",
          {
            href: "#/",
            onclick: (e) => {
              e.preventDefault();
              clearAnswers();
              location.hash = "#/";
            },
          },
          "Start over",
        ),
      ),
      p.answered < p.total_items
        ? h(
            "p",
            { class: "tiny", style: "margin:.4rem 0 0" },
            h(
              "a",
              {
                href: "#/quiz",
                onclick: (e) => {
                  e.preventDefault();
                  const s = loadAnswers() || {};
                  saveAnswers({ ...s, completed: false, resume: true });
                  location.hash = "#/quiz";
                },
              },
              `Answer the other ${p.total_items - p.answered} for a sharper read →`,
            ),
          )
        : null,
      data.notes.length ? h("ul", { class: "notes" }, ...data.notes.map((n) => h("li", {}, n))) : null,
    ),
    hexagon({ user: userHex, size: 150 }),
  );

  const cats = [...new Set(rest.map((r) => r.major.category))].sort();
  let activeCat = null;
  const listEl = h("div", {});
  const filterEls = [
    chip("All", () => setCat(null)),
    ...cats.map((c) => chip(c, () => setCat(c))),
  ];
  const filters = h("div", { class: "filters" }, ...filterEls);

  function setCat(c) {
    activeCat = c;
    filterEls.forEach((el, i) => el.classList.toggle("on", (i === 0 ? null : cats[i - 1]) === c));
    drawList();
  }
  function drawList() {
    clear(listEl);
    rest
      .filter((r) => !activeCat || r.major.category === activeCat)
      .forEach((r) => listEl.append(majorRow(r, userHex)));
  }
  filterEls[0].classList.add("on");
  drawList();

  mount(clear(view),
    isSample
      ? h(
          "p",
          { class: "disclaimer", style: "margin-bottom:1rem" },
          "Sample profile (someone who likes science and hands-on work). ",
          h("a", { href: "#/quiz" }, "Take the quiz"),
          " for your own.",
        )
      : null,
    matchHero,
    profileBar,
    h("h3", { style: "margin:1.8rem 0 .4rem" }, "Other strong fits"),
    h("p", { class: "section-lead tiny" }, "Tap any major to see why."),
    filters,
    listEl,
    h(
      "p",
      { class: "tiny muted", style: "margin-top:1.5rem" },
      `Scored against ${data.n_majors_scored} majors. Data: O*NET ${meta.onet_version}, generated ${meta.data_generated}.`,
    ),
  );
}

const chip = (label, onclick) => h("button", { class: "chip", onclick }, label);

function majorRow(r, userHex) {
  const m = r.major;
  const color = stripeFor(m.high_point_code);
  const row = h(
    "div",
    { class: "card major-row", style: `--stripe:${color}` },
    h("div", { class: "fit" }, String(r.score), h("small", {}, "FIT")),
    h(
      "div",
      {},
      h("h4", {}, m.name),
      h(
        "div",
        { class: "cat", style: "display:flex;gap:.5rem;align-items:center;flex-wrap:wrap" },
        h("span", {}, m.category),
        codeChip(m.high_point_code),
      ),
      h("p", { class: "why" }, m.blurb),
    ),
    h("div", { class: "expand" }, "›"),
  );
  row.addEventListener("click", (e) => {
    if (e.target.tagName === "A" || e.target.closest("a")) return;
    const open = row.classList.toggle("open");
    row.querySelector(".detail")?.remove();
    if (open) row.append(rowDetail(r, userHex));
  });
  return row;
}

function rowDetail(r, userHex) {
  const m = r.major;
  const majorHex = norm(m.riasec, 7);
  const e = r.explanation;
  const reasons = h("div", { class: "reasons" });

  if (e) {
    reasons.append(h("p", { style: "margin:0 0 .9rem;font-size:.92rem" }, e.summary));
  }
  if (e && e.matches.length) {
    reasons.append(
      h("h5", {}, "You line up on"),
      h("div", {}, ...e.matches.map((d) => h("span", { class: "tag pos" }, DIM_LABEL[d]))),
    );
  }
  if (e && e.clashes.length) {
    reasons.append(
      h("h5", { style: "margin-top:.8rem" }, "The major needs, but you rated low"),
      h("div", {}, ...e.clashes.map((d) => h("span", { class: "tag neg" }, DIM_LABEL[d]))),
    );
  }
  if (e && e.helped.length) {
    reasons.append(
      h("h5", { style: "margin-top:.9rem" }, "Answers that pushed this up"),
      h("ul", {}, ...e.helped.slice(0, 4).map((i) => h("li", {}, `${i.text} (${i.delta >= 0 ? "+" : ""}${i.delta})`))),
    );
  }
  if (e && e.hurt.length) {
    reasons.append(
      h("h5", {}, "Answers that pulled it down"),
      h("ul", {}, ...e.hurt.slice(0, 3).map((i) => h("li", {}, `${i.text} (${i.delta})`))),
    );
  }
  reasons.append(
    h("p", { class: "tiny", style: "margin-top:.6rem" }, h("a", { href: "#/major/" + m.slug }, "Full page for " + m.name + " →")),
  );

  return h(
    "div",
    { class: "detail" },
    h(
      "div",
      {},
      hexagon({ user: userHex, major: majorHex, size: 168, animate: false }),
      h("p", { class: "tiny muted", style: "text-align:center;max-width:168px;margin:.3rem auto 0" }, "solid = you, dashed = the major"),
    ),
    reasons,
  );
}

// ---------------------------------------------------------------- browse
async function browse() {
  spinner();
  const { majors } = await ensure("majors", api.majors);
  const byCat = {};
  for (const m of majors) (byCat[m.category] ||= []).push(m);

  mount(clear(view),
    h("h1", { style: "font-size:1.9rem" }, "All majors"),
    h("p", { class: "section-lead" }, `${majors.length} majors, each profiled from the occupations it leads to.`),
    ...Object.keys(byCat)
      .sort()
      .flatMap((cat) => [
        h("h3", { style: "margin:1.8rem 0 .6rem" }, cat),
        h(
          "div",
          { class: "grid-majors" },
          ...byCat[cat].map((m) =>
            h(
              "a",
              { class: "card mini", href: "#/major/" + m.slug, style: `--stripe:${stripeFor(m.high_point_code)}` },
              h("h4", {}, m.name),
              h("div", { class: "tiny muted" }, codeChip(m.high_point_code)),
            ),
          ),
        ),
      ]),
  );
}

// ---------------------------------------------------------------- major detail
async function majorDetail(slug) {
  spinner();
  let m;
  try {
    m = await api.major(slug);
  } catch (err) {
    mount(clear(view),h("p", {}, "Not found: " + err.message), h("p", {}, h("a", { href: "#/majors" }, "Back to all majors")));
    return;
  }
  const { majors } = await ensure("majors", api.majors);
  const saved = loadAnswers();

  let scored = null;
  let userProfileHex = null;
  if (saved && Object.keys(saved.answers || {}).length >= 6) {
    try {
      const cmp = await api.compare(saved.answers, saved.dealbreakers || [], [slug]);
      scored = cmp.results[0];
      const s = await api.score(saved.answers, saved.dealbreakers || [], 1);
      userProfileHex = norm(s.profile.riasec, 4);
    } catch (_) {
      /* no overlay */
    }
  }

  const majorHex = norm(m.riasec, 7);
  const color = stripeFor(m.high_point_code);
  const related = majors
    .filter((x) => x.slug !== m.slug && (x.category === m.category || x.high_point_code[0] === m.high_point_code[0]))
    .slice(0, 6);

  const left = h(
    "div",
    {},
    hexagon({ user: userProfileHex, major: majorHex, size: 260 }),
    userProfileHex
      ? h("p", { class: "tiny muted", style: "text-align:center;margin-top:.4rem" }, "solid = you, dashed = " + m.name)
      : h("p", { class: "tiny muted", style: "text-align:center;margin-top:.4rem" }, h("a", { href: "#/quiz" }, "Take the quiz"), " to overlay your profile"),
    scored ? h("div", { style: "display:grid;place-items:center;margin-top:1rem" }, gauge(scored.score, color)) : null,
  );

  const right = h(
    "div",
    {},
    h("h1", {}, m.name),
    h(
      "div",
      { class: "muted", style: "display:flex;gap:.55rem;align-items:center;flex-wrap:wrap;font-size:.9rem" },
      h("span", {}, m.category),
      h("span", { style: "color:var(--ink-3)" }, "•"),
      codeChip(m.high_point_code),
      h("span", { style: "color:var(--ink-3)" }, "•"),
      h("span", {}, "Job Zone " + m.job_zone.toFixed(1) + " / 5"),
    ),
    h("p", { style: "margin-top:.8rem;font-size:.98rem" }, m.description || m.blurb),
    m.thin_profile
      ? h("p", { class: "tiny", style: "color:var(--warn)" }, `Built from only ${m.n_occupations} occupations, so this profile is approximate.`)
      : null,
    kv("Interests, R to C", RIASEC.map((d) => `${DIM_LABEL[d]} ${m.riasec[d].toFixed(1)}`)),
    kv("Where it leads (labor market, not fit)", m.example_careers),
    m.top_knowledge.length ? kv("Knowledge it draws on", m.top_knowledge) : null,
    h(
      "div",
      { class: "kv" },
      h("h5", {}, "Related majors"),
      h("div", { class: "related" }, ...related.map((x) => h("a", { href: "#/major/" + x.slug }, x.name))),
    ),
    h(
      "p",
      { class: "disclaimer" },
      "A strong interest match means the day-to-day work would probably suit you. It does not mean you would be good at it, or that the field is hiring. Weigh all three.",
    ),
  );

  mount(clear(view),
    h("p", { class: "tiny" }, h("a", { href: "#/majors" }, "← All majors")),
    h("div", { class: "major-detail" }, left, right),
  );
}

const kv = (title, items) =>
  h("div", { class: "kv" }, h("h5", {}, title), h("ul", {}, ...items.map((i) => h("li", {}, i))));

// ---------------------------------------------------------------- about
async function about() {
  const meta = await ensure("meta", api.meta);
  mount(clear(view),
    h("h1", { style: "font-size:1.9rem" }, "How Compass works"),
    aboutSection("The interest inventory", "You answer the O*NET Interest Profiler Short Form, a validated questionnaire from the US Department of Labor. It has 60 items; the quiz asks 30 by default (five per interest) and offers the rest for a sharper read. Your answers become six scores, one for each of Holland's RIASEC interest types."),
    aboutSection("Profiling the majors", "The O*NET database rates every occupation on the same six interests. The government's CIP-to-SOC crosswalk maps each major to the occupations it leads to. Averaging those gives each major a RIASEC profile. A few interdisciplinary majors are mapped to a single teaching occupation by the crosswalk; for those, related occupations are added by hand."),
    aboutSection("Scoring the fit", "The 0-100 score blends the correlation between the shape of your six scores and the major's, with how well your top three interests match the major's as a three-letter code. A dealbreaker you mark lowers a major that leads with that interest."),
    aboutSection("What it does not tell you", "Interest fit is not aptitude, and it is not a forecast of pay or hiring. The major pages show labor-market context separately and clearly labeled."),
    h("p", { class: "tiny muted", style: "margin-top:2rem" }, `Data: O*NET ${meta.onet_version}, ${meta.n_majors} majors, generated ${meta.data_generated}. Sources: ${meta.sources.join("; ")}.`),
  );
}

const aboutSection = (title, body) =>
  h("div", { class: "about-section" }, h("h3", {}, title), h("p", {}, body));

// ---------------------------------------------------------------- sample
function seedSample() {
  const band = { investigative: [3, 4], realistic: [2, 4], conventional: [2, 3], artistic: [0, 2], social: [1, 3], enterprising: [1, 2] };
  const pre = { r: "realistic", i: "investigative", a: "artistic", s: "social", e: "enterprising", c: "conventional" };
  const answers = {};
  for (const p of ["r", "i", "a", "s", "e", "c"]) {
    for (let k = 1; k <= 10; k++) {
      const [lo, hi] = band[pre[p]];
      answers[p + k] = lo + Math.floor(Math.random() * (hi - lo + 1));
    }
  }
  saveAnswers({ answers, ts: Date.now(), sample: true });
  location.hash = "#/results";
}

// ---------------------------------------------------------------- router
const routes = [
  [/^#\/$|^$/, landing],
  [/^#\/quiz$/, quizView],
  [/^#\/results$/, results],
  [/^#\/majors$/, browse],
  [/^#\/major\/(.+)$/, (m) => majorDetail(m[1])],
  [/^#\/about$/, about],
  [/^#\/sample$/, seedSample],
];

function route() {
  if (!location.hash.startsWith("#/quiz")) teardownQuiz();
  const hash = location.hash || "#/";
  for (const [re, fn] of routes) {
    const m = hash.match(re);
    if (m) {
      window.scrollTo(0, 0);
      Promise.resolve(fn(m)).catch((err) => {
        mount(clear(view),h("p", {}, "Something went wrong: " + err.message));
      });
      return;
    }
  }
  landing();
}

window.addEventListener("hashchange", route);
route();
