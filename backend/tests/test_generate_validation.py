from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_rejects_blank_product_name():
    response = client.post(
        "/generate",
        data={"product_name": "", "product_description": "A nice mug"},
    )
    assert response.status_code == 400


def test_generate_requires_an_image():
    response = client.post(
        "/generate",
        data={"product_name": "Mug", "product_description": "A nice mug"},
    )
    assert response.status_code == 400


def test_generate_rejects_unsupported_file_type():
    response = client.post(
        "/generate",
        data={"product_name": "Mug", "product_description": "A nice mug"},
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_get_nonexistent_job_returns_404():
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
