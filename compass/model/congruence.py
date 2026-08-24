"""Score one major against one user profile.

The fit score (0-100) is a blend of two ways of comparing RIASEC profiles:

1. **Shape.** The Pearson correlation between the user's six interest scores and
   the major's six. This rewards profiles with the same *pattern* of highs and
   lows, and ignores overall level, so someone who liked everything a little and
   someone who liked their favourites a lot get the same shape score.

2. **High-point agreement.** How well the user's top three interests line up
   with the major's, as an ordered three-letter code. This is the traditional
   Holland congruence idea and it keeps the result explainable.

A "dealbreaker" the user marked (an interest they never want to use) multiplies
the score down if the major leads with it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from compass.data.schema import RIASEC, RIASEC_LETTER, MajorProfile

from .params import DEFAULT, Params
from .profile import UserProfile

# Rank weights for the three-letter code: first choice counts most.
_RANK_WEIGHT = (3, 2, 1)
_MAX_HIGHPOINT = sum(w * w for w in _RANK_WEIGHT)  # 14, both codes in perfect order


@dataclass(frozen=True)
class DimensionGap:
    dimension: str
    user_z: float
    """The user's score for this interest, standardised within their own profile."""
    major_z: float
    kind: str  # "match" | "clash" | "minor"


@dataclass(frozen=True)
class MajorScore:
    slug: str
    score: int
    shape_r: float
    highpoint_agreement: float
    dealbreaker_hit: bool
    gaps: tuple[DimensionGap, ...]

    @property
    def matches(self) -> tuple[str, ...]:
        return tuple(g.dimension for g in self.gaps if g.kind == "match")

    @property
    def clashes(self) -> tuple[str, ...]:
        return tuple(g.dimension for g in self.gaps if g.kind == "clash")


def _highpoint_agreement(user_code: str, major_code: str) -> float:
    total = 0
    for i, u_letter in enumerate(user_code):
        j = major_code.find(u_letter)
        if j != -1:
            total += _RANK_WEIGHT[i] * _RANK_WEIGHT[j]
    return total / _MAX_HIGHPOINT


def _standardise(vec: np.ndarray) -> np.ndarray:
    centered = vec - vec.mean()
    spread = centered.std()
    return centered / spread if spread > 1e-9 else centered


def _classify_gaps(user_z: np.ndarray, major_z: np.ndarray) -> tuple[DimensionGap, ...]:
    gaps = []
    for i, dim in enumerate(RIASEC):
        uz, mz = float(user_z[i]), float(major_z[i])
        if mz > 0.4 and uz > 0.2:
            kind = "match"
        elif mz > 0.5 and uz < -0.3:
            kind = "clash"
        else:
            kind = "minor"
        gaps.append(DimensionGap(dimension=dim, user_z=round(uz, 2), major_z=round(mz, 2), kind=kind))
    return tuple(gaps)


def score_major(user: UserProfile, major: MajorProfile, params: Params = DEFAULT) -> MajorScore:
    u = np.array(user.scores.as_tuple, dtype=float)
    m = np.array(major.riasec.as_tuple, dtype=float)

    uz = _standardise(u)
    mz = _standardise(m)

    degenerate = uz.std() < 1e-9 or mz.std() < 1e-9
    shape_r = 0.0 if degenerate else float(np.corrcoef(u, m)[0, 1])
    shape_r = max(-1.0, min(1.0, shape_r))

    # Map the correlation to 0-1 over the range that actually carries meaning.
    # A real interest profile rarely correlates below about -0.2 with any major,
    # and everything interesting happens between 0.3 and 1.0, so stretch that
    # band across the whole scale instead of wasting half of it on r < 0.
    shape01 = max(0.0, min(1.0, (shape_r + 0.2) / 1.2))

    user_code = user.scores.high_point_code(params.highpoint_n)
    major_code = major.riasec.high_point_code(params.highpoint_n)
    hp = _highpoint_agreement(user_code, major_code)

    fit = params.shape_weight * shape01 + params.highpoint_weight * hp
    fit = max(0.0, min(1.0, fit))

    dealbreaker_hit = False
    if user.dealbreakers:
        major_top = {RIASEC_LETTER[d] for d in _top_dimensions(m, params.dealbreaker_rank)}
        disliked = {RIASEC_LETTER[d] for d in user.dealbreakers}
        if major_top & disliked:
            fit *= 1.0 - params.dealbreaker_penalty
            dealbreaker_hit = True

    return MajorScore(
        slug=major.slug,
        score=round(100 * fit),
        shape_r=round(shape_r, 3),
        highpoint_agreement=round(hp, 3),
        dealbreaker_hit=dealbreaker_hit,
        gaps=_classify_gaps(uz, mz),
    )


def _top_dimensions(vec: np.ndarray, n: int) -> list[str]:
    order = sorted(range(6), key=lambda i: (-vec[i], i))
    return [RIASEC[i] for i in order[:n]]
