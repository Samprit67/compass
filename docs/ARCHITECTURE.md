# Architecture

Compass is a small monolith: one Python package, a few committed data files, and
a static single-page app served by the same process.

```
compass/
  data/
    schema.py       Riasec, MajorProfile, Question, Answers  (plain dataclasses)
    loader.py       read the committed JSON into those shapes  (cached)
    refresh.py      rebuild major_profiles.json from O*NET + the crosswalk  (dev only)
    majors.yaml         the curated major list
    questionnaire.json  the 60 items
    major_profiles.json the derived profiles
  model/            pure functions, numpy only, no I/O
    params.py    ->  profile.py  ->  congruence.py  ->  explain.py
                                  \-> recommend.py
    pipeline.py     the seam: load data, hand it to the pure code
  api/             FastAPI
    app.py       application factory, error handler, static mount
    routes.py    thin endpoints
    present.py   dataclasses -> JSON dicts (shared with the CLI)
  web/             vanilla ES modules, hand-drawn SVG, no build step
    app.js  quiz.js  charts.js  api.js  format.js  index.html  style.css
  cli.py           Typer app: quiz, score, major, compare, serve, data
```

## The three layers

**`data/` gets the numbers in.** `refresh.py` knows about O*NET's text format
and the crosswalk spreadsheet; `loader.py` knows about the committed JSON.
Neither is imported by the model. The output is two shapes from `schema.py`:
`MajorProfile` (112 of them) and `Questionnaire` (60 items).

**`model/` does the calculation.** Every function takes dataclasses plus a
`Params` and returns dataclasses. No I/O, no globals, no clock. That is what
makes the property tests fast and the score reproducible.

- `build_profile(answers, questionnaire)` -> `UserProfile`
- `score_major(user, major)` -> `MajorScore` (0-100 plus every intermediate)
- `explain(answers, questionnaire, major)` -> `Explanation`
- `recommend(answers, ...)` -> `Recommendation` (ranked, with confidence)

**`api/`, `cli.py`, and `web/` present it.** `present.py` turns a
`Recommendation` into a plain dict; the API returns it as JSON and the CLI
renders it as `rich` tables, both from the same serialiser, so the terminal and
the browser cannot drift apart. The frontend is static files, no bundler.

## Why it is shaped this way

- A **pure model core** makes property-based testing trivial: "more liking of an
  interest never lowers a major led by that interest" is one Hypothesis test.
- **`present.py` shared by the API and the CLI** keeps the two outputs identical.
- **No build step on the frontend**: clone, `compass serve`, done. Drawing the
  interest hexagon by hand in `charts.js` is a constraint that keeps the
  dependency list honest.
- **Committed data, no runtime downloads**: the app has no external dependency
  at request time, so nothing flakes and it deploys anywhere.

## Request flow: `POST /api/score`

1. `routes.score` parses `{answers, dealbreakers, top}` into an `Answers`.
2. `pipeline.evaluate` loads the questionnaire and the 112 profiles (cached
   after the first call) and calls `recommend`.
3. `recommend` builds the user profile, scores all 112 majors, sorts them, and
   attaches an `Explanation` to the top N.
4. `present.recommendation_dict` produces the JSON.

Every step after (1) is pure. A score request is a few milliseconds.
