from fastapi.testclient import TestClient

from src.app import app


def test_retrieve_basic():
    client = TestClient(app)
    payload = {
        "query": "vector db for pg",
        "k": 3,
        "filters": {"topic": ["app-dev"], "since": "P60D"},
    }
    r = client.post("/agent/v1/retrieve/test", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) <= 3
    # top result should be vector/postgres themed
    assert any("Vector DB" in x["title"] for x in data["results"])
