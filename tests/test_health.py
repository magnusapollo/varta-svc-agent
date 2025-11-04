from fastapi.testclient import TestClient
from src.app import app

def test_health_ok():
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'
