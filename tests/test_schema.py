import pytest
from compass.data.schema import RIASEC, Answers, Riasec


def test_riasec_roundtrip():
    r = Riasec.from_iterable([1, 2, 3, 4, 5, 6])
    assert r.as_tuple == (1, 2, 3, 4, 5, 6)
    assert r.as_dict() == dict(zip(RIASEC, (1, 2, 3, 4, 5, 6), strict=True))


def test_riasec_wrong_length():
    with pytest.raises(ValueError):
        Riasec.from_iterable([1, 2, 3])


def test_high_point_code_order_and_ties():
    # investigative highest, then realistic; ties fall back to R-I-A-S-E-C order
    r = Riasec(realistic=5, investigative=6, artistic=5, social=1, enterprising=1, conventional=1)
    assert r.high_point_code(3) == "IRA"
    flat = Riasec(*([3] * 6))
    assert flat.high_point_code(3) == "RIA"


def test_answers_for_dimension_skips_unanswered(questionnaire):
    a = Answers.from_payload({"r1": 4, "r2": 0})
    responses = a.for_dimension(questionnaire, "realistic")
    assert sorted(responses) == [0, 4]


def test_answers_from_payload_coerces_and_normalises_dealbreakers():
    a = Answers.from_payload({"r1": "4"}, ["social", "bogus"])
    assert a.values == {"r1": 4}
    assert a.dealbreakers == frozenset({"social", "bogus"})
