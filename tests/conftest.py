from __future__ import annotations

import pytest
from compass.data.loader import load_profiles, load_questionnaire
from compass.data.schema import Answers


@pytest.fixture(scope="session")
def questionnaire():
    return load_questionnaire()


@pytest.fixture(scope="session")
def profiles():
    return load_profiles()


@pytest.fixture
def persona(questionnaire):
    """Build answers where every item in the named dimensions gets `response`
    and everything else is neutral. `persona(investigative=4, realistic=3)`."""

    def _make(*, dealbreakers=(), default=2, **dim_response):
        values = {q.id: int(dim_response.get(q.dimension, default)) for q in questionnaire.questions}
        return Answers.from_payload(values, dealbreakers)

    return _make
