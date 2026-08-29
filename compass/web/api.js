const BASE = "/api";

async function req(path, opts) {
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      msg = (await res.json()).error || msg;
    } catch (_) {
      /* keep statusText */
    }
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  meta: () => req("/meta"),
  questions: () => req("/questions"),
  majors: () => req("/majors"),
  major: (slug) => req("/majors/" + encodeURIComponent(slug)),
  score: (answers, dealbreakers, top = 15) =>
    req("/score", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ answers, dealbreakers, top }),
    }),
  compare: (answers, dealbreakers, slugs) =>
    req("/compare", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ answers, dealbreakers, slugs }),
    }),
};
