"""REST endpoints. Thin: parse the request, call the model, serialise the result."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from compass import __version__
from compass.data.loader import load_profiles, load_questionnaire, profiles_meta
from compass.data.schema import Answers
from compass.errors import NotFoundError
from compass.model.pipeline import compare, evaluate

from . import present

router = APIRouter()


class ScoreRequest(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)
    dealbreakers: list[str] = Field(default_factory=list)
    top: int = 12


class CompareRequest(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)
    dealbreakers: list[str] = Field(default_factory=list)
    slugs: list[str]


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/meta")
def meta() -> dict:
    m = profiles_meta()
    return {
        "version": __version__,
        "n_majors": m["n_majors"],
        "onet_version": m["onet_version"],
        "data_generated": m["generated"],
        "sources": m["sources"],
    }


@router.get("/questions")
def questions() -> dict:
    return present.questionnaire_dict(load_questionnaire())


@router.get("/majors")
def majors() -> dict:
    return {"majors": [present.major_summary(m) for m in load_profiles()]}


@router.get("/majors/{slug}")
def major(slug: str) -> dict:
    for m in load_profiles():
        if m.slug == slug:
            return present.major_detail(m)
    raise NotFoundError(f"no major with slug {slug!r}")


@router.post("/score")
def score(req: ScoreRequest) -> dict:
    answers = Answers.from_payload(req.answers, req.dealbreakers)
    rec = evaluate(answers, explain_top=max(req.top, 1))
    return present.recommendation_dict(rec, top=max(req.top, 1))


@router.post("/compare")
def compare_majors(req: CompareRequest) -> dict:
    answers = Answers.from_payload(req.answers, req.dealbreakers)
    scored = compare(answers, req.slugs)
    return {"results": [present.scored_major_dict(sm, detail=True) for sm in scored]}


@router.get("/categories")
def categories(_limit: int = Query(default=0, ge=0)) -> dict:
    seen: dict[str, int] = {}
    for m in load_profiles():
        seen[m.category] = seen.get(m.category, 0) + 1
    return {"categories": [{"name": k, "count": v} for k, v in sorted(seen.items())]}
