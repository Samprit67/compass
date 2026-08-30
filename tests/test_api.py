import pytest
from compass.api import create_app
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_meta_and_questions(client):
    assert client.get("/api/meta").json()["n_majors"] > 80
    q = client.get("/api/questions").json()
    assert len(q["questions"]) == 60
    assert len(q["dimensions"]) == 6


def test_majors_list_and_detail(client):
    majors = client.get("/api/majors").json()["majors"]
    assert any(m["slug"] == "computer-science" for m in majors)
    detail = client.get("/api/majors/computer-science").json()
    assert detail["name"] == "Computer Science"
    assert detail["example_careers"]


def test_unknown_major_is_404(client):
    r = client.get("/api/majors/not-a-major")
    assert r.status_code == 404
    assert "error" in r.json()


def test_score_returns_ranked_results_with_explanations(client):
    answers = {f"i{k}": 4 for k in range(1, 11)} | {f"r{k}": 3 for k in range(1, 11)}
    r = client.post("/api/score", json={"answers": answers, "top": 6})
    body = r.json()
    assert body["confidence"] in {"clear", "moderate", "low"}
    scores = [x["score"] for x in body["results"]]
    assert scores == sorted(scores, reverse=True)
    assert "explanation" in body["results"][0]
    assert 0 <= body["results"][0]["score"] <= 100


def test_score_with_no_answers_is_low_confidence(client):
    body = client.post("/api/score", json={"answers": {}}).json()
    assert body["confidence"] == "low"


def test_compare_endpoint(client):
    answers = {f"e{k}": 4 for k in range(1, 11)}
    r = client.post("/api/compare", json={"answers": answers, "slugs": ["finance", "studio-art"]})
    results = r.json()["results"]
    assert [x["major"]["slug"] for x in results] == ["finance", "studio-art"]
    assert results[0]["score"] > results[1]["score"]


def test_web_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Compass" in r.text
