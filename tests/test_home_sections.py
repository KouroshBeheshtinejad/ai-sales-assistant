from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_home_sections_endpoint_returns_arrays():
    response = client.get('/public/home-sections')
    assert response.status_code == 200
    payload = response.json()
    assert 'sections' in payload
    assert isinstance(payload['sections'], list)


def test_admin_home_sections_requires_god_role():
    response = client.get('/admin/home-sections')
    assert response.status_code in {401, 403}
