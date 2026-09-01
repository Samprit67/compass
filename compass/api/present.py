"""Turn the model's dataclasses into plain JSON-ready dicts.

The API returns these and the CLI renders the same dicts as tables, so the two
never drift.
"""

from __future__ import annotations

from compass.data.schema import RIASEC, RIASEC_LETTER, MajorProfile, Questionnaire
from compass.model.explain import Explanation
from compass.model.profile import UserProfile
from compass.model.recommend import Recommendation, ScoredMajor


def riasec_dict(values) -> dict[str, float]:
    return {name: round(v, 2) for name, v in zip(RIASEC, values.as_tuple, strict=True)}


def major_summary(m: MajorProfile) -> dict:
    return {
        "slug": m.slug,
        "name": m.name,
        "category": m.category,
        "blurb": m.blurb,
        "riasec": riasec_dict(m.riasec),
        "high_point_code": m.high_point_code,
    }


def major_detail(m: MajorProfile) -> dict:
    return {
        **major_summary(m),
        "description": m.description,
        "cip_codes": list(m.cip_codes),
        "example_careers": list(m.example_careers),
        "job_zone": m.job_zone,
        "top_knowledge": list(m.top_knowledge),
        "top_skills": list(m.top_skills),
        "n_occupations": m.n_occupations,
        "thin_profile": m.n_occupations < 3,
    }


def questionnaire_dict(q: Questionnaire) -> dict:
    return {
        "title": q.title,
        "source": q.source,
        "response_labels": list(q.response_labels),
        "dimensions": [{"key": name, "letter": RIASEC_LETTER[name]} for name in RIASEC],
        "questions": [{"id": x.id, "text": x.text, "dimension": x.dimension} for x in q.questions],
    }


def profile_dict(p: UserProfile) -> dict:
    return {
        "riasec": riasec_dict(p.scores),
        "high_point_code": p.high_point_code,
        "differentiation": p.differentiation,
        "elevation": p.elevation,
        "answered": p.answered,
        "total_items": p.total_items,
        "dealbreakers": sorted(p.dealbreakers),
    }


def explanation_dict(e: Explanation) -> dict:
    def item(i) -> dict:
        return {
            "id": i.question_id,
            "text": i.text,
            "dimension": i.dimension,
            "response": i.response,
            "delta": i.delta,
        }

    return {
        "summary": e.summary,
        "matches": list(e.matches),
        "clashes": list(e.clashes),
        "helped": [item(i) for i in e.helped],
        "hurt": [item(i) for i in e.hurt],
    }


def scored_major_dict(sm: ScoredMajor, *, detail: bool = False) -> dict:
    out = {
        "major": major_detail(sm.major) if detail else major_summary(sm.major),
        "score": sm.score.score,
        "shape_r": sm.score.shape_r,
        "highpoint_agreement": sm.score.highpoint_agreement,
        "dealbreaker_hit": sm.score.dealbreaker_hit,
        "gaps": [
            {"dimension": g.dimension, "user_z": g.user_z, "major_z": g.major_z, "kind": g.kind}
            for g in sm.score.gaps
        ],
    }
    if sm.explanation is not None:
        out["explanation"] = explanation_dict(sm.explanation)
    return out


def recommendation_dict(rec: Recommendation, *, top: int) -> dict:
    ranked = rec.top(top)
    return {
        "profile": profile_dict(rec.profile),
        "confidence": rec.confidence,
        "notes": list(rec.notes),
        "results": [scored_major_dict(sm) for sm in ranked],
        "n_majors_scored": len(rec.ranked),
    }
