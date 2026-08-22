"""Every tunable constant in the model, with where the value comes from.

If you are about to hard-code a number in ``congruence.py`` or ``recommend.py``,
put it here instead. ``docs/METHODOLOGY.md`` walks through what each one does.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    # -- response scale -------------------------------------------------------
    neutral_response: int = 2
    """Midpoint of the Interest Profiler's 0-4 scale ("Not sure"). Unanswered
    items are treated as this."""

    max_response: int = 4

    # -- congruence blend ---------------------------------------------------
    shape_weight: float = 0.70
    """How much the fit score leans on the *shape* of the two interest profiles
    (their correlation) versus their high-point agreement. Shape carries most of
    the weight because it uses all six numbers, not just the top three."""

    highpoint_weight: float = 0.30
    """Weight on matching the top interests as letters. This is how Holland
    congruence is traditionally scored, and it keeps the result legible: "you
    and this major are both I-C-R"."""

    highpoint_n: int = 3
    """Length of the interest code compared (the classic three-letter code)."""

    # -- dealbreakers -----------------------------------------------------
    dealbreaker_penalty: float = 0.35
    """A major loses this fraction of its score if it *leads* with an interest
    the user marked as a hard no. Chosen so a dealbreaker demotes a major
    clearly without zeroing it (interests are not destiny)."""

    dealbreaker_rank: int = 2
    """"Leads with" means the disliked interest is in the major's top this-many."""

    # -- confidence -----------------------------------------------------
    low_differentiation: float = 0.20
    """If the spread between the user's highest and lowest interest, as a
    fraction of the scale, is below this, the profile is "flat" and the ranking
    is reported as low-confidence. Interest inventories are only informative
    when some interests stand out."""

    moderate_differentiation: float = 0.35

    min_answers_for_confidence: int = 40
    """Of 60 items. Below this the ranking is downgraded one confidence level."""

    # -- explanation ------------------------------------------------------
    explain_top_positive: int = 4
    explain_top_negative: int = 3


DEFAULT = Params()
