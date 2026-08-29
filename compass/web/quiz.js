import { h, clear, saveAnswers } from "./format.js";

/**
 * Render the questionnaire into `mount`. Calls `onDone(answers)` when finished
 * (answers is {qid: 0..4}). `start` lets a resumed quiz jump back in.
 */
export function runQuiz(mount, questionnaire, { answers = {}, onDone }) {
  const items = questionnaire.questions;
  const labels = questionnaire.response_labels;
  let idx = Object.keys(answers).length;
  if (idx >= items.length) idx = items.length - 1;

  const bar = h("span");
  const progress = h("div", { class: "progress" }, bar);
  const count = h("div", { class: "q-count" });
  const qtext = h("div", { class: "q-text" });
  const scale = h("div", { class: "scale" });
  const back = h("button", { onclick: () => go(idx - 1) }, "← Back");
  const skip = h("button", { class: "ghost", onclick: () => choose(2) }, "Not sure");
  const nav = h("div", { class: "quiz-nav" }, back, skip);

  const root = h("div", { class: "quiz" }, progress, count, qtext, scale, nav);
  clear(mount).append(root);

  function choose(value) {
    answers[items[idx].id] = value;
    saveAnswers({ answers, ts: Date.now() });
    if (idx + 1 >= items.length) {
      onDone(answers);
    } else {
      go(idx + 1);
    }
  }

  function go(n) {
    idx = Math.max(0, Math.min(items.length - 1, n));
    render();
  }

  function render() {
    const item = items[idx];
    bar.style.width = ((idx / items.length) * 100).toFixed(1) + "%";
    count.textContent = `Activity ${idx + 1} of ${items.length}`;
    qtext.textContent = "Would you enjoy: " + lowerFirst(item.text) + "?";
    back.disabled = idx === 0;
    clear(scale);
    labels.forEach((label, v) => {
      const btn = h(
        "button",
        { class: answers[item.id] === v ? "sel" : "", onclick: () => choose(v) },
        h("span", { class: "key" }, String(v + 1)),
        label,
      );
      scale.append(btn);
    });
  }

  function onKey(e) {
    if (e.key >= "1" && e.key <= "5") choose(Number(e.key) - 1);
    else if (e.key === "ArrowLeft") go(idx - 1);
  }
  document.addEventListener("keydown", onKey);
  mount.addEventListener("quiz:teardown", () => document.removeEventListener("keydown", onKey), { once: true });

  render();
}

function lowerFirst(s) {
  return s.charAt(0).toLowerCase() + s.slice(1);
}
