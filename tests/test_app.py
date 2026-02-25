import pytest

from main import create_app


@pytest.fixture
def client():
    app = create_app(testing=True)
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


def test_create_link_endpoint(client):
    payload = {"original_url": "https://example.com/long-url", "short_name": "exmpl"}
    response = client.post("/api/links", json=payload)

    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] is not None
    assert data["original_url"] == payload["original_url"]
    assert data["short_name"] == payload["short_name"]
    assert data["short_url"].endswith("/r/exmpl")


def test_list_links_empty(client):
    response = client.get("/api/links")

    assert response.status_code == 200
    assert response.get_json() == []
    assert response.headers.get("Content-Range") == "links 0-0/0"


def test_list_links_contains_created(client):
    payload = {"original_url": "https://example.com/long-url", "short_name": "exmpl"}
    create_resp = client.post("/api/links", json=payload)
    assert create_resp.status_code == 201

    list_resp = client.get("/api/links")
    assert list_resp.status_code == 200
    assert list_resp.headers.get("Content-Range") == "links 0-0/1"

    data = list_resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    assert item["id"] is not None
    assert item["original_url"] == payload["original_url"]
    assert item["short_name"] == payload["short_name"]
    assert item["short_url"].endswith("/r/exmpl")


def test_redirect_short_link_success(client):
    # Создаём короткую ссылку
    payload = {"original_url": "https://example.com", "short_name": "man"}
    create_resp = client.post("/api/links", json=payload)
    assert create_resp.status_code == 201

    # Проверяем, что /r/<short_name> отдаёт редирект
    resp = client.get("/r/man", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers.get("Location") == "https://example.com"


def test_redirect_short_link_not_found(client):
    resp = client.get("/r/not-exists", follow_redirects=False)
    assert resp.status_code == 404


def test_get_link_by_id_not_found(client):
    response = client.get("/api/links/999999")

    assert response.status_code == 404
    data = response.get_json()
    assert isinstance(data, dict)
    assert "detail" in data
    assert isinstance(data["detail"], str)


def test_get_link_by_id_success(client):
    payload = {"original_url": "https://example.com/long-url", "short_name": "exmpl"}
    create_resp = client.post("/api/links", json=payload)
    assert create_resp.status_code == 201

    created = create_resp.get_json()
    link_id = created["id"]

    get_resp = client.get(f"/api/links/{link_id}")
    assert get_resp.status_code == 200

    data = get_resp.get_json()
    assert data["id"] == link_id
    assert data["original_url"] == payload["original_url"]
    assert data["short_name"] == payload["short_name"]
    assert data["short_url"].endswith("/r/exmpl")


def test_delete_link_not_found(client):
    resp = client.delete("/api/links/999999")
    assert resp.status_code == 404
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "detail" in data
    assert isinstance(data["detail"], str)


def test_delete_link_success(client):
    payload = {"original_url": "https://example.com/long-url", "short_name": "exmpl"}
    create_resp = client.post("/api/links", json=payload)
    assert create_resp.status_code == 201
    link_id = create_resp.get_json()["id"]

    del_resp = client.delete(f"/api/links/{link_id}")
    assert del_resp.status_code == 204
    assert del_resp.data == b""  # тело пустое

    # Проверяем, что удалилось
    get_resp = client.get(f"/api/links/{link_id}")
    assert get_resp.status_code == 404


def test_put_link_not_found(client):
    payload = {"original_url": "https://example.com/new", "short_name": "new1"}
    resp = client.put("/api/links/999999", json=payload)

    assert resp.status_code == 404
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "detail" in data
    assert isinstance(data["detail"], str)


def test_put_link_invalid_payload(client):
    # Нет нужных полей
    resp = client.put("/api/links/1", json={"original_url": "https://example.com"})
    assert resp.status_code == 422
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "detail" in data


def test_put_link_success(client):
    # Создаём ссылку
    create_payload = {"original_url": "https://example.com/old", "short_name": "old1"}
    create_resp = client.post("/api/links", json=create_payload)
    assert create_resp.status_code == 201
    link_id = create_resp.get_json()["id"]

    # Обновляем
    update_payload = {"original_url": "https://example.com/new", "short_name": "new1"}
    put_resp = client.put(f"/api/links/{link_id}", json=update_payload)

    assert put_resp.status_code == 200
    data = put_resp.get_json()
    assert data["id"] == link_id
    assert data["original_url"] == update_payload["original_url"]
    assert data["short_name"] == update_payload["short_name"]
    assert data["short_url"].endswith("/r/new1")

    # Проверяем через GET, что реально обновилось
    get_resp = client.get(f"/api/links/{link_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.get_json()
    assert get_data["original_url"] == update_payload["original_url"]
    assert get_data["short_name"] == update_payload["short_name"]


def test_put_link_conflict(client):
    # Создаём две ссылки
    a = {"original_url": "https://example.com/a", "short_name": "a1"}
    b = {"original_url": "https://example.com/b", "short_name": "b1"}

    resp_a = client.post("/api/links", json=a)
    resp_b = client.post("/api/links", json=b)

    assert resp_a.status_code == 201
    assert resp_b.status_code == 201

    a_id = resp_a.get_json()["id"]

    # Пытаемся обновить A так, чтобы short_name стал уже занятым (b1)
    conflict_payload = {"original_url": "https://example.com/a2", "short_name": "b1"}
    put_resp = client.put(f"/api/links/{a_id}", json=conflict_payload)

    assert put_resp.status_code == 409
    assert put_resp.get_json() == {"error": "short_name already exists"}


# Helpers and pagination tests
def _seed_n_links(client, n: int):
    for i in range(n):
        payload = {
            "original_url": f"https://example.com/{i}",
            "short_name": f"seed-{i}",
        }
        res = client.post("/api/links", json=payload)
        assert res.status_code == 201


def test_links_pagination_first_10(client):
    _seed_n_links(client, 11)

    res = client.get("/api/links?range=[0,10]")
    assert res.status_code == 200
    assert res.headers.get("Content-Range") == "links 0-9/11"

    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 10


def test_links_pagination_skip_5_take_5(client):
    _seed_n_links(client, 11)

    res = client.get("/api/links?range=[5,10]")
    assert res.status_code == 200
    assert res.headers.get("Content-Range") == "links 5-9/11"

    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) == 5

