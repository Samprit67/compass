from compass.model.explain import explain


def test_explanation_names_matches_and_a_helping_answer(persona, questionnaire, profiles):
    cs = next(m for m in profiles if m.slug == "computer-science")
    answers = persona(investigative=4, conventional=4, realistic=3, artistic=0, social=0)
    e = explain(answers, questionnaire, cs)
    assert "investigative" in e.matches or "conventional" in e.matches
    assert e.helped, "a strong-fit major should cite at least one answer that helped"
    assert all(i.dimension in {"realistic", "investigative", "conventional"} for i in e.helped)


def test_explanation_flags_a_clash(persona, questionnaire, profiles):
    art = next(m for m in profiles if m.slug == "studio-art")
    answers = persona(artistic=0, social=0, investigative=4, conventional=4)
    e = explain(answers, questionnaire, art)
    assert "artistic" in e.clashes
    assert "rated low" in e.summary


def test_helped_delta_is_positive_and_hurt_is_negative(persona, questionnaire, profiles):
    nursing = next(m for m in profiles if m.slug == "nursing")
    answers = persona(social=4, investigative=3, realistic=1, artistic=1, enterprising=1, conventional=1)
    e = explain(answers, questionnaire, nursing)
    assert all(i.delta >= 0 for i in e.helped)
    assert all(i.delta <= 0 for i in e.hurt)
