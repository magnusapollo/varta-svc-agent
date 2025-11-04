import json
from starlette.testclient import TestClient
from src.app import app

def test_chat_stream_sse():
    client = TestClient(app)
    payload = {"message":"What's new in app dev this week?","filters":{"topic":["app-dev"],"since":"P14D"}}
    with client.stream("POST", "/agent/v1/chat/stream", json=payload) as r:
        assert r.status_code == 200
        chunks = list(r.iter_lines())
        assert any(str(chunk).startswith("b'event: token") for chunk in chunks)
        assert any(str(chunk).startswith("b'event: citations") for chunk in chunks)
        assert any(str(chunk).startswith("b'event: done") for chunk in chunks)
