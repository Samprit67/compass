import numpy as np
from compass.data.schema import MajorProfile, Riasec
from compass.model.congruence import score_major
from compass.model.profile import build_profile
from hypothesis import given, settings
from hypothesis import strategies as st

RESP = st.integers(min_value=0, max_value=4)


def _major(vec, slug="x"):
    return MajorProfile(
        slug=slug,
        name=slug,
        category="test",
        blurb="",
        cip_codes=(),
        riasec=Riasec.from_iterable(vec),
        example_careers=(),
        job_zone=4.0,
        top_knowledge=(),
        top_skills=(),
        n_occupations=5,
    )


def test_score_is_bounded(persona, questionnaire, profiles):
    p = build_profile(persona(investigative=4, artistic=3), questionnaire)
    for major in profiles:
        s = score_major(p, major)
        assert 0 <= s.score <= 100


def test_identical_shape_scores_near_top(persona, questionnaire, profiles):
    cs = next(m for m in profiles if m.slug == "computer-science")
    # answer so the user's profile shape matches CS: high I and C, low A and S
    answers = persona(investigative=4, conventional=4, realistic=3, artistic=0, social=0, enterprising=1)
    p = build_profile(answers, questionnaire)
    ranked = sorted(profiles, key=lambda m: -score_major(p, m).score)
    assert cs.slug in {m.slug for m in ranked[:5]}


@given(likes=RESP, base=RESP)
@settings(max_examples=25, deadline=None)
def test_more_liking_never_lowers_a_major_led_by_that_interest(likes, base, questionnaire, profiles):
    if likes <= base:
        return
    art_major = next(m for m in profiles if m.high_point_code[0] == "A")

    def answers_with(a_response):
        vals = {q.id: (a_response if q.dimension == "artistic" else base) for q in questionnaire.questions}
        from compass.data.schema import Answers

        return build_profile(Answers.from_payload(vals), questionnaire)

    low = score_major(answers_with(base), art_major).score
    high = score_major(answers_with(likes), art_major).score
    assert high >= low


def test_dealbreaker_demotes_a_major_that_leads_with_it(persona, questionnaire, profiles):
    social_major = next(m for m in profiles if m.high_point_code[0] == "S")
    plain = build_profile(persona(social=4, investigative=3), questionnaire)
    with_db = build_profile(persona(social=4, investigative=3, dealbreakers=["social"]), questionnaire)
    assert score_major(with_db, social_major).score < score_major(plain, social_major).score
    assert score_major(with_db, social_major).dealbreaker_hit


def test_flat_profile_gives_no_shape_signal(questionnaire, profiles):
    from compass.data.schema import Answers

    flat = build_profile(Answers.from_payload({q.id: 2 for q in questionnaire.questions}), questionnaire)
    scores = [score_major(flat, m) for m in profiles]
    assert all(s.shape_r == 0.0 for s in scores)


def test_a_profile_identical_to_a_major_scores_it_perfectly():
    from compass.model.profile import UserProfile

    v = [1, 7, 1, 1, 4, 5]  # interest code I-C-E
    user = UserProfile(
        scores=Riasec.from_iterable(v),
        differentiation=1.0,
        elevation=0.5,
        answered=60,
        total_items=60,
        dealbreakers=frozenset(),
    )
    s = score_major(user, _major(v))
    assert s.highpoint_agreement == 1.0
    assert np.isclose(s.shape_r, 1.0)
    assert s.score >= 95
