"""Turn a set of questionnaire answers into a user interest profile.

The output is deliberately small: six averaged scores plus two summary numbers
(how spiky the profile is, and how enthusiastic overall). Everything downstream
works off this.
"""

from __future__ import annotations

from dataclasses import dataclass

from compass.data.schema import RIASEC, Answers, Questionnaire, Riasec

from .params import DEFAULT, Params


@dataclass(frozen=True)
class UserProfile:
    scores: Riasec
    """Mean response for each interest, on the questionnaire's 0-4 scale.
    Dimensions with no answers sit at the neutral midpoint."""

    differentiation: float
    """(highest interest minus lowest) divided by the scale maximum, so 0 to 1.
    A spiky profile (clear favourites) is close to 1; a flat one is near 0."""

    elevation: float
    """Mean of the six scores over the scale maximum, 0 to 1. High means the
    user liked most activities regardless of type."""

    answered: int
    total_items: int
    dealbreakers: frozenset[str]

    @property
    def high_point_code(self) -> str:
        return self.scores.high_point_code()

    @property
    def answered_fraction(self) -> float:
        return self.answered / self.total_items if self.total_items else 0.0


def build_profile(
    answers: Answers,
    questionnaire: Questionnaire,
    params: Params = DEFAULT,
) -> UserProfile:
    per_dim: list[float] = []
    for dim in RIASEC:
        responses = answers.for_dimension(questionnaire, dim)
        if responses:
            per_dim.append(sum(responses) / len(responses))
        else:
            per_dim.append(float(params.neutral_response))

    scores = Riasec.from_iterable(per_dim)
    scale = float(params.max_response)
    differentiation = (max(per_dim) - min(per_dim)) / scale
    elevation = (sum(per_dim) / len(per_dim)) / scale

    valid_ids = {q.id for q in questionnaire.questions}
    answered = sum(1 for qid in answers.values if qid in valid_ids)

    # Keep only dealbreakers that name a real dimension.
    dealbreakers = frozenset(d for d in answers.dealbreakers if d in RIASEC)

    return UserProfile(
        scores=scores,
        differentiation=round(differentiation, 4),
        elevation=round(elevation, 4),
        answered=answered,
        total_items=len(questionnaire.questions),
        dealbreakers=dealbreakers,
    )
