from compass.data.loader import load_profiles, load_questionnaire, profiles_meta
from compass.data.schema import RIASEC


def test_profiles_load_and_are_well_formed():
    majors = load_profiles()
    assert len(majors) > 80
    slugs = [m.slug for m in majors]
    assert len(slugs) == len(set(slugs))
    for m in majors:
        assert m.name and m.category and m.blurb
        assert len(m.riasec.as_tuple) == 6
        assert all(1.0 <= v <= 7.0 for v in m.riasec.as_tuple)
        assert m.cip_codes
        assert 0.0 <= m.job_zone <= 5.0
        assert m.n_occupations >= 1


def test_every_high_point_letter_appears_somewhere():
    codes = "".join(m.high_point_code for m in load_profiles())
    for letter in "RIASEC":
        assert letter in codes, f"no major leads anywhere near {letter}"


def test_questionnaire_is_60_items_10_per_dimension():
    q = load_questionnaire()
    assert len(q.questions) == 60
    by_dim = q.by_dimension()
    assert all(len(by_dim[d]) == 10 for d in RIASEC)
    assert q.max_response == 4


def test_meta_has_sources():
    meta = profiles_meta()
    assert meta["onet_version"]
    assert meta["sources"]
