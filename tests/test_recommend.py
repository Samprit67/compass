from compass.data.schema import Answers
from compass.model.pipeline import compare, evaluate
from compass.model.recommend import recommend


def test_ranked_descending_and_complete(persona, questionnaire, profiles):
    rec = recommend(persona(investigative=4), questionnaire=questionnaire, majors=profiles)
    scores = [sm.score.score for sm in rec.ranked]
    assert scores == sorted(scores, reverse=True)
    assert len(rec.ranked) == len(profiles)


def test_explanations_only_on_top_n(persona, questionnaire, profiles):
    rec = recommend(persona(artistic=4), questionnaire=questionnaire, majors=profiles, explain_top=5)
    assert all(sm.explanation is not None for sm in rec.ranked[:5])
    assert all(sm.explanation is None for sm in rec.ranked[5:])


def test_flat_profile_is_low_confidence(questionnaire, profiles):
    flat = Answers.from_payload({q.id: 2 for q in questionnaire.questions})
    rec = recommend(flat, questionnaire=questionnaire, majors=profiles)
    assert rec.confidence == "low"
    assert rec.notes


def test_partial_answers_downgrade_confidence(persona, questionnaire, profiles):
    answers = Answers.from_payload({"i1": 4, "i2": 4, "r1": 0})  # 3 of 60
    rec = recommend(answers, questionnaire=questionnaire, majors=profiles)
    assert rec.confidence in {"moderate", "low"}
    assert any("of 60" in n for n in rec.notes)


def test_science_persona_puts_stem_on_top(persona, questionnaire, profiles):
    rec = recommend(
        persona(investigative=4, realistic=3, conventional=3, artistic=0, social=1, enterprising=1),
        questionnaire=questionnaire,
        majors=profiles,
        explain_top=0,
    )
    top_cats = {sm.major.category for sm in rec.ranked[:8]}
    assert {"Computing & Data", "Engineering", "Life Sciences", "Physical Sciences"} & top_cats


def test_helper_persona_puts_people_work_on_top(persona, questionnaire, profiles):
    rec = recommend(
        persona(social=4, artistic=2, investigative=2, realistic=1, enterprising=1, conventional=1),
        questionnaire=questionnaire,
        majors=profiles,
        explain_top=0,
    )
    top = {sm.major.slug for sm in rec.ranked[:10]}
    assert top & {"social-work", "nursing", "elementary-education", "special-education", "psychology"}


def test_evaluate_and_compare_wire_up(persona):
    rec = evaluate(persona(enterprising=4), explain_top=3)
    assert rec.ranked and rec.ranked[0].explanation is not None
    pair = compare(persona(enterprising=4), ["finance", "studio-art"])
    assert [sm.major.slug for sm in pair] == ["finance", "studio-art"]
    assert pair[0].score.score > pair[1].score.score
