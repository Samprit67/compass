from compass.data.schema import Answers
from compass.model.profile import build_profile


def test_unanswered_dimensions_sit_at_neutral(questionnaire):
    profile = build_profile(Answers.from_payload({}), questionnaire)
    assert profile.scores.as_tuple == (2, 2, 2, 2, 2, 2)
    assert profile.differentiation == 0.0
    assert profile.answered == 0


def test_spiky_profile_has_high_differentiation(persona, questionnaire):
    profile = build_profile(persona(investigative=4, realistic=0), questionnaire)
    assert profile.differentiation == 1.0  # (4 - 0) / 4
    assert profile.high_point_code[0] == "I"


def test_elevation_tracks_overall_enthusiasm(persona, questionnaire):
    low = build_profile(persona(default=1), questionnaire)
    high = build_profile(persona(default=4), questionnaire)
    assert high.elevation > low.elevation
    # both flat, so neither is differentiated
    assert low.differentiation == 0.0 and high.differentiation == 0.0


def test_answered_count_ignores_unknown_ids(questionnaire):
    profile = build_profile(Answers.from_payload({"r1": 3, "not_a_real_id": 4}), questionnaire)
    assert profile.answered == 1
