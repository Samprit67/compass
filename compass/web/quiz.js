import { h, clear, saveAnswers } from "./format.js";

const PER_PAGE = 10;
const HALF = 30; // the default run; the rest is optional

/**
 * Paged grid questionnaire. Defaults to 30 items (3 pages); after that the user
 * can stop or answer 30 more. `onDone(answers)` gets {qid: 0..4}.
 */
export function runQuiz(mount, questionnaire, { answers = {}, onDone }) {
  const items = questionnaire.questions;
  const labels = questionnaire.response_labels;
  const totalPages = Math.ceil(items.length / PER_PAGE);
  const halfPages = HALF / PER_PAGE;

  let extended = Object.keys(answers).length >= HALF;
  const cap = () => (extended ? totalPages : halfPages);
  const target = () => (extended ? items.length : HALF);
  // Resume on the first page that still has an unanswered item.
  let page = 0;
  for (let pg = 0; pg < cap(); pg++) {
    const on = items.slice(pg * PER_PAGE, pg * PER_PAGE + PER_PAGE);
    if (on.some((it) => answers[it.id] === undefined)) {
      page = pg;
      break;
    }
    page = Math.min(pg + 1, cap() - 1);
  }

  const root = h("div", { class: "quiz" });
  clear(mount).append(root);

  const answeredCount = () => Object.keys(answers).length;

  function setAnswer(id, v) {
    answers[id] = v;
    saveAnswers({ answers, ts: Date.now() });
    renderPage();
  }

  function renderPage() {
    clear(root);
    const start = page * PER_PAGE;
    const slice = items.slice(start, start + PER_PAGE);
    const done = answeredCount();
    const goal = target();

    root.append(
      h(
        "div",
        { class: "quiz-head" },
        h("span", { class: "step" }, `Part ${page + 1} of ${cap()}`),
        h("span", { class: "tiny muted" }, `${Math.min(done, goal)} of ${goal}`),
      ),
      h("div", { class: "progress" }, h("span", { style: `width:${Math.min(1, done / goal) * 100}%` })),
      h(
        "p",
        { class: "quiz-sub" },
        "How much would you enjoy each activity? Use the whole range, and skip any you are unsure about.",
      ),
    );

    const grid = h("div", { class: "q-grid" });
    for (const item of slice) {
      const cur = answers[item.id];
      const dots = h(
        "div",
        { class: "dots" },
        ...labels.map((label, v) =>
          h("button", {
            "data-v": v,
            class: cur === v ? "on" : "",
            title: label,
            "aria-label": label,
            onclick: () => setAnswer(item.id, v),
          }),
        ),
      );
      grid.append(
        h(
          "div",
          { class: "q-item" + (cur !== undefined ? " answered" : "") },
          h("span", { class: "label" }, upperFirst(item.text)),
          dots,
        ),
      );
    }
    root.append(grid);
    root.append(
      h(
        "div",
        { class: "scale-legend" },
        h("span", {}, labels[0]),
        h("span", {}, labels[labels.length - 1]),
      ),
    );

    const back = h("button", { disabled: page === 0, onclick: () => go(page - 1) }, "← Back");
    const atHalf = !extended && page + 1 >= halfPages;
    const atEnd = extended && page + 1 >= totalPages;

    let nav;
    if (atHalf || atEnd) {
      const seeResults = h("button", { class: "primary", onclick: finish }, "See my results");
      const more = atHalf
        ? h(
            "button",
            {
              onclick: () => {
                extended = true;
                go(page + 1);
              },
            },
            "Answer 30 more →",
          )
        : null;
      nav = h("div", { class: "quiz-nav" }, back, h("div", { style: "display:flex;gap:.6rem" }, more, seeResults));
    } else {
      const next = h("button", { class: "primary", onclick: () => go(page + 1) }, "Next →");
      const skipEarly =
        answeredCount() >= 20
          ? h("button", { class: "ghost skip", onclick: finish }, "Skip to results")
          : null;
      nav = h("div", { class: "quiz-nav" }, back, h("div", { style: "display:flex;gap:.6rem" }, skipEarly, next));
    }
    root.append(nav);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function go(n) {
    page = Math.max(0, Math.min(cap() - 1, n));
    renderPage();
  }

  function finish() {
    onDone(answers);
  }

  function onKey(e) {
    if (e.key === "ArrowRight" && page + 1 < cap()) go(page + 1);
    else if (e.key === "ArrowLeft") go(page - 1);
  }
  document.addEventListener("keydown", onKey);
  mount.addEventListener("quiz:teardown", () => document.removeEventListener("keydown", onKey), { once: true });

  renderPage();
}

function upperFirst(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
