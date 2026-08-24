def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "app" in response.json()
