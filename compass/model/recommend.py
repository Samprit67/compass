"""Rank every major for a set of answers, and say how much to trust the ranking."""

from __future__ import annotations

from dataclasses import dataclass

from compass.data.schema import Answers, MajorProfile, Questionnaire

from .congruence import MajorScore, score_major
from .explain import Explanation, explain
from .params import DEFAULT, Params
from .profile import UserProfile, build_profile


@dataclass(frozen=True)
class ScoredMajor:
    major: MajorProfile
    score: MajorScore
    explanation: Explanation | None


@dataclass(frozen=True)
class Recommendation:
    profile: UserProfile
    ranked: tuple[ScoredMajor, ...]
    confidence: str  # "clear" | "moderate" | "low"
    notes: tuple[str, ...]

    def top(self, n: int) -> tuple[ScoredMajor, ...]:
        return self.ranked[:n]

    def by_category(self) -> dict[str, list[ScoredMajor]]:
        out: dict[str, list[ScoredMajor]] = {}
        for sm in self.ranked:
            out.setdefault(sm.major.category, []).append(sm)
        return out


def _confidence(profile: UserProfile, params: Params) -> tuple[str, list[str]]:
    notes: list[str] = []
    level = "clear"

    if profile.differentiation < params.low_differentiation:
        level = "low"
        notes.append(
            "Your interests came out fairly even, so no major stands out strongly. "
            "Treat the ranking as a loose guide and lean on the individual major pages."
        )
    elif profile.differentiation < params.moderate_differentiation:
        level = "moderate"
        notes.append(
            "You have some clear interests but a lot of the middle is close. "
            "The top handful matter more than the exact order."
        )

    if profile.answered < params.min_answers_for_confidence:
        notes.append(
            f"You answered {profile.answered} of {profile.total_items} activities. "
            "Answering the rest will sharpen the result."
        )
        level = {"clear": "moderate", "moderate": "low", "low": "low"}[level]

    if profile.elevation > 0.8:
        notes.append(
            "You liked almost every activity. That is common, and the ranking still "
            "reflects which interests you rated highest relative to the others."
        )

    return level, notes


def recommend(
    answers: Answers,
    *,
    questionnaire: Questionnaire,
    majors: tuple[MajorProfile, ...],
    params: Params = DEFAULT,
    explain_top: int = 12,
) -> Recommendation:
    profile = build_profile(answers, questionnaire, params)

    scored = [(major, score_major(profile, major, params)) for major in majors]
    scored.sort(key=lambda pair: (-pair[1].score, pair[0].name))

    ranked: list[ScoredMajor] = []
    for rank, (major, sc) in enumerate(scored):
        exp = explain(answers, questionnaire, major, params) if rank < explain_top else None
        ranked.append(ScoredMajor(major=major, score=sc, explanation=exp))

    confidence, notes = _confidence(profile, params)
    return Recommendation(profile=profile, ranked=tuple(ranked), confidence=confidence, notes=tuple(notes))
