"""Read the committed data files into the typed shapes from ``schema.py``.

The app and the tests only ever call these. Regenerating ``major_profiles.json``
is ``data/refresh.py``'s job.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from compass.errors import DataError

from .schema import RIASEC, MajorProfile, Question, Questionnaire, Riasec

_HERE = Path(__file__).parent
_PROFILES_PATH = _HERE / "major_profiles.json"
_QUESTIONNAIRE_PATH = _HERE / "questionnaire.json"


@lru_cache(maxsize=1)
def load_profiles() -> tuple[MajorProfile, ...]:
    try:
        doc = json.loads(_PROFILES_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - packaging failure
        raise DataError(f"cannot read {_PROFILES_PATH.name}: {exc}") from exc

    order = doc["meta"]["riasec_order"]
    if tuple(order) != RIASEC:
        raise DataError(f"{_PROFILES_PATH.name} RIASEC order {order} does not match schema {RIASEC}")

    majors = []
    for m in doc["majors"]:
        majors.append(
            MajorProfile(
                slug=m["slug"],
                name=m["name"],
                category=m["category"],
                blurb=m["blurb"],
                description=m.get("description", m["blurb"]),
                cip_codes=tuple(m["cip_codes"]),
                riasec=Riasec.from_iterable(m["riasec"]),
                example_careers=tuple(m["example_careers"]),
                job_zone=float(m["job_zone"]),
                top_knowledge=tuple(m["top_knowledge"]),
                top_skills=tuple(m["top_skills"]),
                n_occupations=int(m["n_occupations"]),
            )
        )
    if not majors:
        raise DataError(f"{_PROFILES_PATH.name} has no majors")
    return tuple(majors)


@lru_cache(maxsize=1)
def load_questionnaire() -> Questionnaire:
    try:
        doc = json.loads(_QUESTIONNAIRE_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - packaging failure
        raise DataError(f"cannot read {_QUESTIONNAIRE_PATH.name}: {exc}") from exc

    return Questionnaire(
        title=doc["title"],
        source=doc["source"],
        response_labels=tuple(doc["response_labels"]),
        questions=tuple(
            Question(id=q["id"], text=q["text"], dimension=q["dimension"]) for q in doc["questions"]
        ),
    )


@lru_cache(maxsize=1)
def profiles_meta() -> dict:
    return json.loads(_PROFILES_PATH.read_text())["meta"]
