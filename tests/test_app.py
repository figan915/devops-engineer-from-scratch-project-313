import pytest
from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")


    assert response.status_code == 200
    assert "ping" in response.data.decode()


def test_ping_endpoint(client):
    response = client.get("/ping")


    assert response.status_code == 200
    assert response.data.decode() == "pong"


def test_404_headler(client):
    response = client.get("/not-exists")


    assert response.status_code == 404
    assert response.data.decode() == "Page Not Found"

