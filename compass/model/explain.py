"""Explain a single major's fit score in terms of the user's actual answers.

Two views:

* **Dimension level** - which interests the user and the major both rank highly
  (matches), and which the major leans on that the user does not (clashes).
* **Item level** - for the interests the major is built on, the specific
  activities the user rated highest and lowest, with a sensitivity check on how
  much each of those answers actually moved the score.
"""

from __future__ import annotations

from dataclasses import dataclass

from compass.data.schema import DIM_ADJECTIVE, RIASEC, Answers, MajorProfile, Questionnaire

from .congruence import score_major
from .params import DEFAULT, Params
from .profile import build_profile


@dataclass(frozen=True)
class ItemInfluence:
    question_id: str
    text: str
    dimension: str
    response: int
    delta: int
    """Score points this answer is worth: the fit score now, minus what it would
    be if this one answer had been neutral instead. Positive means the answer
    helped the major, negative means it hurt it."""


@dataclass(frozen=True)
class Explanation:
    slug: str
    summary: str
    matches: tuple[str, ...]
    clashes: tuple[str, ...]
    helped: tuple[ItemInfluence, ...]
    hurt: tuple[ItemInfluence, ...]


_PHRASING = {
    "realistic": "hands-on, building and fixing",
    "investigative": "research and figuring things out",
    "artistic": "creative and expressive work",
    "social": "helping and teaching people",
    "enterprising": "leading, persuading, and selling",
    "conventional": "organising data and systems",
}


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _summary(
    major: MajorProfile,
    score: int,
    matches: tuple[str, ...],
    clashes: tuple[str, ...],
) -> str:
    m = major.riasec.as_tuple
    top_two = [RIASEC[i] for i in sorted(range(6), key=lambda i: -m[i])[:2]]
    character = _join([DIM_ADJECTIVE[d] for d in top_two])

    if score >= 78:
        verdict = "and that matches your interests closely"
    elif score >= 55:
        verdict = "which overlaps with your interests"
    elif score >= 35:
        verdict = "which only partly overlaps with your interests"
    else:
        verdict = "which is not where your interests point"

    tail = ""
    if clashes:
        tail = f" It leans on {_join([_PHRASING[c] for c in clashes[:2]])}, which you rated low."
    return f"{major.name} is {character} work, {verdict}.{tail}"


def _delta(
    answers: Answers,
    questionnaire: Questionnaire,
    major: MajorProfile,
    params: Params,
    base_score: int,
    qid: str,
) -> int:
    counterfactual = Answers(
        values={**answers.values, qid: params.neutral_response},
        dealbreakers=answers.dealbreakers,
    )
    neutral = score_major(build_profile(counterfactual, questionnaire, params), major, params)
    return base_score - neutral.score


def explain(
    answers: Answers,
    questionnaire: Questionnaire,
    major: MajorProfile,
    params: Params = DEFAULT,
) -> Explanation:
    profile = build_profile(answers, questionnaire, params)
    base = score_major(profile, major, params)

    # The interests this major is actually built on.
    m = major.riasec.as_tuple
    key_dims = {RIASEC[i] for i in sorted(range(6), key=lambda i: -m[i])[: params.highpoint_n]}

    text_by_id = {q.id: q.text for q in questionnaire.questions}
    dim_by_id = {q.id: q.dimension for q in questionnaire.questions}

    # Candidate items: answered items in the major's key interests.
    answered = [
        (qid, answers.values[qid])
        for qid in answers.values
        if qid in text_by_id and dim_by_id[qid] in key_dims
    ]

    def influence(qid: str, resp: int) -> ItemInfluence:
        return ItemInfluence(
            question_id=qid,
            text=text_by_id[qid],
            dimension=dim_by_id[qid],
            response=resp,
            delta=_delta(answers, questionnaire, major, params, base.score, qid),
        )

    likes = [influence(qid, r) for qid, r in answered if r >= 3]
    dislikes = [influence(qid, r) for qid, r in answered if r <= 1]
    # Lead with the answer that moved the score most, then by strength of response.
    likes.sort(key=lambda i: (-i.delta, -i.response))
    dislikes.sort(key=lambda i: (i.delta, i.response))

    helped = tuple(likes[: params.explain_top_positive])
    hurt = tuple(dislikes[: params.explain_top_negative])

    return Explanation(
        slug=major.slug,
        summary=_summary(major, base.score, base.matches, base.clashes),
        matches=base.matches,
        clashes=base.clashes,
        helped=helped,
        hurt=hurt,
    )
