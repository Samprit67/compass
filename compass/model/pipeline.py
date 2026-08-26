"""The one call the API and CLI make: answers in, ranked recommendation out.

Everything under ``model/`` is pure. This module is the seam where the committed
data files get loaded and handed to the pure code.
"""

from __future__ import annotations

from compass.data.loader import load_profiles, load_questionnaire
from compass.data.schema import Answers
from compass.errors import NotFoundError

from .explain import explain
from .params import DEFAULT, Params
from .recommend import Recommendation, ScoredMajor, recommend


def evaluate(
    answers: Answers,
    *,
    params: Params = DEFAULT,
    explain_top: int = 12,
) -> Recommendation:
    return recommend(
        answers,
        questionnaire=load_questionnaire(),
        majors=load_profiles(),
        params=params,
        explain_top=explain_top,
    )


def compare(answers: Answers, slugs: list[str], *, params: Params = DEFAULT) -> list[ScoredMajor]:
    by_slug = {m.slug: m for m in load_profiles()}
    questionnaire = load_questionnaire()
    from .congruence import score_major
    from .profile import build_profile

    profile = build_profile(answers, questionnaire, params)
    out: list[ScoredMajor] = []
    for slug in slugs:
        major = by_slug.get(slug)
        if major is None:
            raise NotFoundError(f"no major with slug {slug!r}")
        out.append(
            ScoredMajor(
                major=major,
                score=score_major(profile, major, params),
                explanation=explain(answers, questionnaire, major, params),
            )
        )
    return out
