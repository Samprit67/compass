# Contributing

Thanks for taking a look.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install        # optional, runs ruff on commit
```

## Before you push

```bash
make check                # ruff, mypy, and pytest, the same as CI
```

## Conventions

- **The model core is pure.** Functions in `compass/model/` take dataclasses and
  a `Params` and return dataclasses. No I/O, no globals, no reading the clock.
- **Every model constant lives in `params.py`**, with a comment. If you are
  hard-coding a number in `congruence.py` or `recommend.py`, move it.
- **New model behaviour needs a property test** where one makes sense:
  monotonicity, bounds, ordering.
- **Tests stay offline.** The ETL is tested against a synthetic slice built in a
  tmpdir; do not add large fixture files or reach for the network.
- **User-facing failures** subclass `compass.errors.CompassError`. Anything else
  is a bug and should crash loudly.
- Line length is 108. `ruff format` is the source of truth.

## Adding a major

Add an entry to [`compass/data/majors.yaml`](compass/data/majors.yaml):

```yaml
  - slug: data-engineering
    name: Data Engineering
    category: Computing & Data
    blurb: "Building the pipelines and stores that make data usable."
    cip: ["11.0899"]
    extra_soc: ["15-2051"]   # optional: occupations the crosswalk misses
```

Then `python -m compass.data.refresh` and check the profile looks right
(`compass major "Data Engineering"`).

## Good first issues

- Add wage and 10-year growth per major from a reachable labor-market source.
- A "why not" view: the highest-scoring major in each category you did *not*
  match, and what would have to be different.
- Let the user re-weight the six interests before ranking.
- Import an existing RIASEC score (from a school counsellor) instead of taking
  the quiz.
