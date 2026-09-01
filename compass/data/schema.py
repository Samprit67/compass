"""The typed shapes the rest of Compass passes around.

Two families live here:

* ``Riasec`` and ``MajorProfile`` describe the *data* (an occupation-or-major
  interest profile built from O*NET).
* ``Question``, ``Questionnaire`` and ``Answers`` describe the *questionnaire*
  (the O*NET Interest Profiler Short Form the user fills in).

Nothing in this module does I/O or math. ``data/loader.py`` reads it from disk;
``model/`` computes on it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

# Holland's six interest types, in the canonical R-I-A-S-E-C order. Every vector
# in Compass is stored in this order so that positions line up without a lookup.
RIASEC: tuple[str, ...] = (
    "realistic",
    "investigative",
    "artistic",
    "social",
    "enterprising",
    "conventional",
)
RIASEC_LETTER: dict[str, str] = {name: name[0].upper() for name in RIASEC}
LETTER_RIASEC: dict[str, str] = {v: k for k, v in RIASEC_LETTER.items()}

# Short adjective for each interest, for one-line explanations.
DIM_ADJECTIVE: dict[str, str] = {
    "realistic": "hands-on",
    "investigative": "analytical",
    "artistic": "creative",
    "social": "people-focused",
    "enterprising": "enterprising",
    "conventional": "methodical",
}


@dataclass(frozen=True)
class Riasec:
    """Six interest scores in R-I-A-S-E-C order.

    The unit depends on where it came from: O*NET occupational-interest values
    are on a 1 to 7 scale, a user's raw Interest Profiler scores are 0 to 40, and
    a z-scored profile is centred on 0. The model normalises before it compares,
    so the class itself stays unit-agnostic.
    """

    realistic: float
    investigative: float
    artistic: float
    social: float
    enterprising: float
    conventional: float

    @classmethod
    def from_iterable(cls, values: Iterable[float]) -> Riasec:
        vals = [float(v) for v in values]
        if len(vals) != 6:
            raise ValueError(f"a RIASEC vector needs exactly 6 values, got {len(vals)}")
        return cls(*vals)

    @classmethod
    def from_mapping(cls, values: Mapping[str, float]) -> Riasec:
        return cls.from_iterable(values[name] for name in RIASEC)

    @property
    def as_tuple(self) -> tuple[float, float, float, float, float, float]:
        return (
            self.realistic,
            self.investigative,
            self.artistic,
            self.social,
            self.enterprising,
            self.conventional,
        )

    def as_dict(self) -> dict[str, float]:
        return dict(zip(RIASEC, self.as_tuple, strict=True))

    def high_point_code(self, n: int = 3) -> str:
        """The n highest interests as letters, e.g. ``"IRC"``. Ties break by the
        canonical R-I-A-S-E-C order, which is how O*NET itself orders them."""
        order = sorted(range(6), key=lambda i: (-self.as_tuple[i], i))
        return "".join(RIASEC_LETTER[RIASEC[i]] for i in order[:n])


@dataclass(frozen=True)
class MajorProfile:
    """A college major, with the interest profile built from the occupations it
    leads to (via the CIP to SOC crosswalk) and their O*NET data."""

    slug: str
    name: str
    category: str
    blurb: str
    """One line, shown on cards."""
    description: str
    """A short paragraph on what the major is, shown on its page."""
    cip_codes: tuple[str, ...]
    riasec: Riasec
    """Employment-unweighted mean of the interest profiles of this major's
    occupations, on O*NET's 1 to 7 scale."""
    example_careers: tuple[str, ...]
    job_zone: float
    """Mean O*NET Job Zone (1 = little preparation, 5 = extensive) of the
    occupations, i.e. how much schooling the field typically expects."""
    top_knowledge: tuple[str, ...]
    top_skills: tuple[str, ...]
    n_occupations: int

    @property
    def high_point_code(self) -> str:
        return self.riasec.high_point_code()


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    dimension: str  # one of RIASEC


@dataclass(frozen=True)
class Questionnaire:
    """The Interest Profiler item set, plus the response anchors."""

    title: str
    source: str
    response_labels: tuple[str, ...]  # index 0..N-1, low interest to high
    questions: tuple[Question, ...]

    def __post_init__(self) -> None:
        seen = set()
        for q in self.questions:
            if q.dimension not in RIASEC:
                raise ValueError(f"question {q.id!r} has unknown dimension {q.dimension!r}")
            if q.id in seen:
                raise ValueError(f"duplicate question id {q.id!r}")
            seen.add(q.id)

    @property
    def max_response(self) -> int:
        return len(self.response_labels) - 1

    def by_dimension(self) -> dict[str, tuple[Question, ...]]:
        out: dict[str, list[Question]] = {name: [] for name in RIASEC}
        for q in self.questions:
            out[q.dimension].append(q)
        return {k: tuple(v) for k, v in out.items()}


@dataclass(frozen=True)
class Answers:
    """What the user submitted: question id -> response index (0..max_response).

    Unanswered questions are simply absent; the model treats them as neutral.
    """

    values: Mapping[str, int]
    dealbreakers: frozenset[str] = field(default_factory=frozenset)
    """Dimensions the user marked as hard nos, e.g. ``{"realistic"}``."""

    def for_dimension(self, questionnaire: Questionnaire, dimension: str) -> list[int]:
        ids = [q.id for q in questionnaire.questions if q.dimension == dimension]
        return [self.values[qid] for qid in ids if qid in self.values]

    @classmethod
    def from_payload(
        cls,
        values: Mapping[str, int],
        dealbreakers: Sequence[str] = (),
    ) -> Answers:
        clean = {str(k): int(v) for k, v in values.items()}
        return cls(values=clean, dealbreakers=frozenset(dealbreakers))
