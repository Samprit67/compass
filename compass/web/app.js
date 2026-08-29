import { api } from "./api.js";
import { hexagon, norm } from "./charts.js";
import {
  h,
  clear,
  RIASEC,
  DIM_LABEL,
  LETTER,
  loadAnswers,
  saveAnswers,
  clearAnswers,
} from "./format.js";
import { runQuiz } from "./quiz.js";

const view = document.getElementById("view");
let CACHE = { questionnaire: null, majors: null, meta: null };

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
  return clear(view).append(h("div", { class: "spinner" }));
}

async function ensure(key, loader) {
  if (!CACHE[key]) CACHE[key] = await loader();
  return CACHE[key];
}

function teardownQuiz() {
  view.dispatchEvent(new Event("quiz:teardown"));
}

// ---------------------------------------------------------------- landing
function landing() {
  const answers = loadAnswers();
  const cta = h("div", { class: "cta" });
  if (answers && Object.keys(answers.answers || {}).length >= 6) {
    cta.append(
      h("button", { class: "primary", onclick: () => (location.hash = "#/results") }, "See my results"),
      h("button", { onclick: () => (location.hash = "#/quiz") }, "Retake the quiz"),
    );
  } else {
    cta.append(
      h("button", { class: "primary", onclick: () => (location.hash = "#/quiz") }, "Take the quiz"),
      h("button", { onclick: () => (location.hash = "#/sample") }, "See a sample result"),
    );
  }

  const pillars = h(
    "div",
    { class: "pillars" },
    pillar("Real interest data", "Every major is profiled from O*NET, the interest database career counselors use, mapped through the government's CIP-to-SOC crosswalk."),
    pillar("It shows its work", "Each recommendation tells you which of your answers drove it, and where you and the major do not line up."),
    pillar("Honest about limits", "Interest fit is one signal. It is not aptitude, and it is not a prediction of the job market."),
  );

  clear(view).append(
    h(
      "section",
      { class: "hero" },
      h("h1", {}, "Find a major that fits how you like to work"),
      h("p", { class: "lede" }, "A 60-question interest inventory, scored against 112 college majors, with the reasoning shown."),
      cta,
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
  runQuiz(view, q, {
    answers: saved ? { ...saved.answers } : {},
    onDone: (answers) => {
      saveAnswers({ answers, ts: Date.now() });
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
  const data = await api.score(saved.answers, saved.dealbreakers || [], 20);
  renderResults(data, meta, !!saved.sample);
}

function renderResults(data, meta, isSample) {
  const p = data.profile;
  const userHex = norm(p.riasec, 4);

  const head = h(
    "div",
    { class: "card results-head" },
    h(
      "div",
      {},
      h("h2", {}, "Your interest profile ", h("span", { class: "code-chip" }, p.high_point_code)),
      h(
        "p",
        { class: "muted tiny" },
        `Answered ${p.answered} of ${p.total_items}. `,
        h("span", { class: "conf " + data.confidence }, data.confidence + " confidence"),
      ),
      data.notes.length ? h("ul", { class: "notes" }, ...data.notes.map((n) => h("li", {}, n))) : null,
      h(
        "p",
        { class: "tiny", style: "margin-top:.8rem" },
        h("a", { href: "#/quiz" }, "Retake"),
        " · ",
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
    ),
    hexagon({ user: userHex, size: 200 }),
  );

  const cats = [...new Set(data.results.map((r) => r.major.category))].sort();
  let activeCat = null;
  const list = h("div", {});
  const filters = h(
    "div",
    { class: "filters" },
    chip("All", true, () => setCat(null)),
    ...cats.map((c) => chip(c, false, () => setCat(c))),
  );

  function setCat(c) {
    activeCat = c;
    [...filters.children].forEach((el, i) => {
      const label = i === 0 ? null : cats[i - 1];
      el.classList.toggle("on", label === c);
    });
    drawList();
  }

  function drawList() {
    clear(list);
    data.results
      .filter((r) => !activeCat || r.major.category === activeCat)
      .forEach((r, i) => list.append(majorRow(r, userHex, i)));
  }

  filters.firstChild.classList.add("on");
  drawList();

  clear(view).append(
    isSample
      ? h(
          "p",
          { class: "disclaimer", style: "margin-bottom:1rem" },
          "This is a sample profile (someone who likes science and hands-on work). ",
          h("a", { href: "#/quiz" }, "Take the quiz"),
          " for your own.",
        )
      : null,
    head,
    h("h3", { style: "margin:1.6rem 0 .8rem" }, "Best-fitting majors"),
    filters,
    list,
    h(
      "p",
      { class: "tiny muted", style: "margin-top:1.5rem" },
      `Scored against ${data.n_majors_scored} majors. Data: O*NET ${meta.onet_version}, generated ${meta.data_generated}.`,
    ),
  );
}

const chip = (label, on, onclick) => h("button", { class: "chip" + (on ? " on" : ""), onclick }, label);

function majorRow(r, userHex, rank) {
  const m = r.major;
  const row = h(
    "div",
    { class: "card major-row" },
    h("div", { class: "fit" }, String(r.score), h("small", {}, "FIT")),
    h(
      "div",
      {},
      h("h4", {}, m.name, " ", rank === 0 ? h("span", { class: "tag pos" }, "top match") : null),
      h("div", { class: "cat" }, m.category + "  ·  interest code " + m.high_point_code),
      h("p", { class: "why" }, r.explanation ? r.explanation.summary : m.blurb),
    ),
    h("div", { class: "expand", html: "&#8250;" }),
  );
  row.addEventListener("click", (e) => {
    if (e.target.tagName === "A") return;
    const open = row.classList.toggle("open");
    const existing = row.querySelector(".detail");
    if (existing) existing.remove();
    if (open) row.append(rowDetail(r, userHex));
  });
  return row;
}

function rowDetail(r, userHex) {
  const m = r.major;
  const majorHex = norm(m.riasec, 7);
  const e = r.explanation;
  const reasons = h("div", { class: "reasons" });

  if (e && e.matches.length) {
    reasons.append(
      h("h5", {}, "You line up on"),
      h("div", {}, ...e.matches.map((d) => h("span", { class: "tag pos" }, DIM_LABEL[d]))),
    );
  }
  if (e && e.clashes.length) {
    reasons.append(
      h("h5", { style: "margin-top:.7rem" }, "The major leans on, but you did not"),
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
    h("p", { class: "tiny", style: "margin-top:.9rem" }, h("a", { href: "#/major/" + m.slug }, "Full page for " + m.name + " →")),
  );

  return h(
    "div",
    { class: "detail" },
    h(
      "div",
      {},
      hexagon({ user: userHex, major: majorHex, size: 170, animate: false }),
      h("p", { class: "tiny muted", style: "text-align:center;max-width:170px" }, "solid = you, dashed = the major"),
    ),
    reasons,
  );
}

// ---------------------------------------------------------------- browse majors
async function browse() {
  spinner();
  const { majors } = await ensure("majors", api.majors);
  const byCat = {};
  for (const m of majors) (byCat[m.category] ||= []).push(m);

  clear(view).append(
    h("h2", {}, "All majors"),
    h("p", { class: "muted" }, `${majors.length} majors, each profiled from the occupations it leads to.`),
    ...Object.keys(byCat)
      .sort()
      .flatMap((cat) => [
        h("h3", { style: "margin:1.6rem 0 .6rem" }, cat),
        h(
          "div",
          { class: "grid-majors" },
          ...byCat[cat].map((m) =>
            h(
              "a",
              { class: "card mini", href: "#/major/" + m.slug },
              h("h4", {}, m.name),
              h("div", { class: "tiny muted" }, "interest code " + m.high_point_code),
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
    clear(view).append(h("p", {}, "Not found: " + err.message), h("p", {}, h("a", { href: "#/majors" }, "Back to all majors")));
    return;
  }
  const [{ majors }] = await Promise.all([ensure("majors", api.majors)]);
  const saved = loadAnswers();

  let scored = null;
  if (saved && Object.keys(saved.answers || {}).length >= 6) {
    try {
      const cmp = await api.compare(saved.answers, saved.dealbreakers || [], [slug]);
      scored = cmp.results[0];
    } catch (_) {
      /* no score overlay */
    }
  }

  const majorHex = norm(m.riasec, 7);
  const userProfileHex = saved ? await userHexFromAnswers(saved) : null;

  const related = majors
    .filter((x) => x.slug !== m.slug && (x.category === m.category || sharePrefix(x.high_point_code, m.high_point_code)))
    .slice(0, 6);

  const left = h(
    "div",
    {},
    hexagon({ user: userProfileHex, major: majorHex, size: 240 }),
    userProfileHex
      ? h("p", { class: "tiny muted", style: "text-align:center" }, "solid = you, dashed = " + m.name)
      : h("p", { class: "tiny muted", style: "text-align:center" }, h("a", { href: "#/quiz" }, "Take the quiz"), " to overlay your profile"),
    scored
      ? h(
          "p",
          { style: "text-align:center;margin-top:.6rem" },
          h("span", { class: "fit", style: "font-size:2rem" }, String(scored.score)),
          h("div", { class: "tiny muted" }, "your fit"),
        )
      : null,
  );

  const right = h(
    "div",
    {},
    h("h1", {}, m.name),
    h("div", { class: "muted" }, m.category + "  ·  interest code " + m.high_point_code + "  ·  Job Zone " + m.job_zone.toFixed(1) + "/5"),
    h("p", {}, m.blurb),
    m.thin_profile
      ? h("p", { class: "tiny", style: "color:var(--warn)" }, `Built from only ${m.n_occupations} occupations, so this profile is approximate.`)
      : null,
    kv("Interests, R to C", RIASEC.map((d) => `${DIM_LABEL[d]} ${m.riasec[d].toFixed(1)}`)),
    kv("Where it leads (labor market, not fit)", m.example_careers),
    m.top_knowledge.length ? kv("Knowledge it draws on", m.top_knowledge) : null,
    h("div", { class: "kv" }, h("h5", {}, "Related majors"), h("div", { class: "related" }, ...related.map((x) => h("a", { href: "#/major/" + x.slug }, x.name)))),
    h(
      "p",
      { class: "disclaimer" },
      "A strong interest match means the day-to-day work would probably suit you. It does not mean you would be good at it, or that the field is hiring. Weigh all three.",
    ),
  );

  clear(view).append(h("p", { class: "tiny" }, h("a", { href: "#/majors" }, "← All majors")), h("div", { class: "major-detail" }, left, right));
}

async function userHexFromAnswers(saved) {
  try {
    const data = await api.score(saved.answers, saved.dealbreakers || [], 1);
    return norm(data.profile.riasec, 4);
  } catch (_) {
    return null;
  }
}

const kv = (title, items) =>
  h("div", { class: "kv" }, h("h5", {}, title), h("ul", {}, ...items.map((i) => h("li", {}, i))));

function sharePrefix(a, b) {
  return a && b && a[0] === b[0];
}

// ---------------------------------------------------------------- about
async function about() {
  const meta = await ensure("meta", api.meta);
  clear(view).append(
    h("h2", {}, "How Compass works"),
    section("The interest inventory", "You answer the 60-item O*NET Interest Profiler Short Form, a validated questionnaire from the US Department of Labor. Your answers become six scores, one for each of Holland's RIASEC interest types: Realistic, Investigative, Artistic, Social, Enterprising, Conventional."),
    section("Profiling the majors", "The O*NET database rates every occupation on the same six interests. The government's CIP-to-SOC crosswalk maps each college major to the occupations it leads to. Averaging those gives each major a RIASEC profile. A few interdisciplinary majors are mapped to a single teaching occupation by the crosswalk; for those, a handful of related occupations are added by hand."),
    section("Scoring the fit", "The fit score blends two comparisons: the correlation between the shape of your six scores and the major's, and how well your top three interests match the major's as a three-letter code. A dealbreaker you mark lowers a major's score if it leads with that interest."),
    section("What it does not tell you", "Interest fit is not aptitude, and it is not a forecast of pay or hiring. The major pages show labor-market context separately, and clearly labeled."),
    h("p", { class: "tiny muted", style: "margin-top:2rem" }, `Data: O*NET ${meta.onet_version}, ${meta.n_majors} majors, generated ${meta.data_generated}. Sources: ${meta.sources.join("; ")}.`),
  );
}

const section = (title, body) => h("div", { style: "margin:1.2rem 0" }, h("h3", {}, title), h("p", { class: "muted" }, body));

// ---------------------------------------------------------------- sample profile
// Seeds a plausible "likes science and building things" profile so someone can
// see a full result without answering 60 questions first.
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
        clear(view).append(h("p", {}, "Something went wrong: " + err.message));
      });
      return;
    }
  }
  landing();
}

window.addEventListener("hashchange", route);
route();
