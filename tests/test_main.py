from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from image_converter.converter import convert_image
from image_converter.main import app

client = TestClient(app)


def _png() -> bytes:
    image = Image.new("RGBA", (8, 8), (255, 0, 0, 128))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_convert_png_to_webp() -> None:
    response = client.post(
        "/api/convert",
        params={"output_format": "webp", "preset": "lossless"},
        content=_png(),
        headers={"X-Relative-Path": "produtos/camisa.png"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert "camisa.webp" in response.headers["content-disposition"]


def test_convert_rejects_unknown_preset() -> None:
    response = client.post(
        "/api/convert",
        params={"output_format": "webp", "preset": "tiny"},
        content=_png(),
        headers={"X-Relative-Path": "foto.png"},
    )

    assert response.status_code == 400


def test_convert_accepts_webp_input() -> None:
    webp = convert_image(_png(), "WEBP")

    response = client.post(
        "/api/convert",
        params={"output_format": "avif", "preset": "mobile"},
        content=webp,
        headers={"X-Relative-Path": "foto.webp"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/avif"
