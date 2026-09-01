# Methodology

How Compass turns 60 answers into a ranked list of majors. Every constant named
here lives in [`compass/model/params.py`](../compass/model/params.py) with a
comment, and every step is a pure function in
[`compass/model/`](../compass/model/). The API and `compass score --json` return
every intermediate value.

## 0. The interest framework

Compass uses **Holland's RIASEC model**, the standard in vocational psychology:
six interest types arranged on a hexagon so that adjacent types are similar and
opposite types are not.

| letter | type | likes |
|---|---|---|
| R | Realistic | tools, machines, plants, animals, being outside |
| I | Investigative | ideas, research, figuring out why |
| A | Artistic | self-expression, design, performance |
| S | Social | teaching, helping, working with people |
| E | Enterprising | leading, persuading, selling, running things |
| C | Conventional | data, records, order, clear procedures |

## 1. Your profile (`profile.py`)

You answer the activities on a 0-4 scale, strongly dislike to strongly like. The
questionnaire has 60 items, ten per interest; the quiz asks 30 by default (five
per interest) and offers the other 30 for a sharper read. Your score for an
interest is the **mean of your answers to its activities**; unanswered activities
are treated as the neutral midpoint (2).

Two summary numbers come out of this:

- **Differentiation** `= (highest interest - lowest) / 4`. Between 0 and 1. A
  spiky profile with clear favourites is near 1; a flat one is near 0. Interest
  inventories are only informative when some interests stand out, so a low
  differentiation downgrades the whole result to low-confidence.
- **Elevation** `= mean of the six scores / 4`. High elevation means you liked
  most activities regardless of type. It does not change the ranking (the shape
  match ignores level) but it is surfaced as a note.

## 2. Profiling a major (`data/refresh.py`, run once)

Each major in [`majors.yaml`](../compass/data/majors.yaml) lists one or more
2020 CIP codes. The build:

1. Looks up the SOC occupation codes each CIP maps to, in the **NCES CIP-to-SOC
   crosswalk**. Cross-field catch-alls like "Managers, All Other" are dropped
   (see [`DATA.md`](DATA.md)).
2. Expands each 6-digit SOC to its O*NET detailed occupations and pulls their
   **RIASEC ratings** (the O*NET "Occupational Interests" scale, 1 to 7).
3. Drops occupations below Job Zone 3, since a four-year major mostly prepares
   you for Job Zone 4-5 work, unless that leaves fewer than two occupations.
4. Averages the remaining occupations' RIASEC vectors. That mean, on the 1-to-7
   scale, is the major's interest profile.

Majors the crosswalk maps to a single teaching occupation get a few related
occupations added by hand (`extra_soc` in `majors.yaml`) and are flagged
`thin`.

## 3. The fit score (`congruence.py`)

For a user profile `u` (six values, 0-4) and a major profile `m` (six values,
1-7):

### Shape match

```
shape_r  = pearson_correlation(u, m)          # -1 to 1, 0 if either is flat
shape01  = clip((shape_r + 0.2) / 1.2, 0, 1)  # stretch the meaningful band
```

The correlation compares the *pattern* of the two profiles and ignores overall
level. It is rescaled because a real interest profile almost never correlates
below about -0.2 with any major, and everything interesting happens between 0.3
and 1.0, so the raw `(r + 1) / 2` would waste half the scale.

### High-point match

Take each side's top three interests as an ordered code (e.g. `ICR`). For every
letter in the user's code at rank `i` that also appears in the major's code at
rank `j`, add `weight[i] * weight[j]` where `weight = (3, 2, 1)`. Divide by 14
(a perfect ordered match). This is an Iachan-style congruence index and it is
what makes the result explainable: "you and this major are both I-C-R."

### Blend

```
fit = 0.70 * shape01 + 0.30 * highpoint          # params.shape_weight, highpoint_weight
```

Shape carries most of the weight because it uses all six numbers. High-point
match keeps the result legible and stops a near-tie on shape from feeling
arbitrary.

### Dealbreakers

If you mark an interest as a hard no and the major has that interest in its
**top two**, the fit is multiplied by `1 - 0.35`. A dealbreaker demotes a major
clearly without zeroing it, because interests are not destiny.

```
score = round(100 * fit)
```

## 4. Explanation (`explain.py`)

For a shown major, Compass reports:

- **Matches**: interests where your standardised score and the major's are both
  clearly above their own means.
- **Clashes**: interests the major is high on (above its mean) where you are
  clearly below yours.
- **Helped / hurt items**: your highest- and lowest-rated activities *within the
  major's top three interests*, each with a **delta**: how many points the fit
  score would drop (or rise) if that one answer had been neutral instead. The
  delta is a one-at-a-time sensitivity check; it compresses near the top of the
  scale, where any single answer matters less.

## 5. Confidence (`recommend.py`)

| condition | effect |
|---|---|
| differentiation < 0.20 | confidence = low, with a note that no major stands out |
| differentiation < 0.35 | confidence = moderate |
| fewer than 28 answered | confidence drops one level, with a note |
| elevation > 0.8 | a note that you liked almost everything |

## Things this gets wrong

- **High-usage judgement calls.** The crosswalk, not Compass, decides which
  occupations a major "leads to". It is conservative: it maps English mostly to
  teaching and editing, and misses the many English majors who go into law,
  marketing, or product.
- **Averaging flattens range.** A major that spans very different occupations
  (Biology: field ecologist to lab geneticist) gets a profile in the middle that
  matches nobody exactly.
- **Interest is measured, not tested.** A strong Investigative score means you
  *like* investigative work, not that you are good at the math it takes.
