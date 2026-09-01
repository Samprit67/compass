import { h, clear, saveAnswers } from "./format.js";

const PER_PAGE = 10;
const ENOUGH_TO_FINISH = 20; // once this many are answered, offer "see results"

/**
 * Paged grid questionnaire. `onDone(answers)` gets {qid: 0..4}.
 */
export function runQuiz(mount, questionnaire, { answers = {}, onDone }) {
  const items = questionnaire.questions;
  const labels = questionnaire.response_labels;
  const pages = Math.ceil(items.length / PER_PAGE);
  let page = Math.min(Math.floor(Object.keys(answers).length / PER_PAGE), pages - 1);

  const root = h("div", { class: "quiz" });
  clear(mount).append(root);

  const answeredCount = () => Object.keys(answers).length;

  function setAnswer(id, v) {
    answers[id] = v;
    saveAnswers({ answers, ts: Date.now() });
    render();
  }

  function render() {
    clear(root);
    const start = page * PER_PAGE;
    const slice = items.slice(start, start + PER_PAGE);
    const done = answeredCount();

    root.append(
      h(
        "div",
        { class: "quiz-head" },
        h("span", { class: "step" }, `Part ${page + 1} of ${pages}`),
        h("span", { class: "tiny muted" }, `${done} of ${items.length} answered`),
      ),
      h("div", { class: "progress" }, h("span", { style: `width:${(done / items.length) * 100}%` })),
      h(
        "p",
        { class: "quiz-sub" },
        "How much would you enjoy each activity? Skip any you are unsure about.",
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
    const forwardLabel = page + 1 >= pages ? "See my results" : "Next →";
    const forward = h(
      "button",
      { class: "primary", onclick: () => (page + 1 >= pages ? finish() : go(page + 1)) },
      forwardLabel,
    );
    const nav = h("div", { class: "quiz-nav" }, back, forward);
    if (page + 1 < pages && done >= ENOUGH_TO_FINISH) {
      nav.insertBefore(
        h("button", { class: "ghost skip", onclick: finish }, "That is enough, show results"),
        forward,
      );
    }
    root.append(nav);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function go(n) {
    page = Math.max(0, Math.min(pages - 1, n));
    render();
  }

  function finish() {
    onDone(answers);
  }

  function onKey(e) {
    if (e.key === "ArrowRight" && page + 1 < pages) go(page + 1);
    else if (e.key === "ArrowLeft") go(page - 1);
  }
  document.addEventListener("keydown", onKey);
  mount.addEventListener("quiz:teardown", () => document.removeEventListener("keydown", onKey), { once: true });

  render();
}

function upperFirst(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
