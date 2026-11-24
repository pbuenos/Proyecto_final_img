"""Pruebas de los endpoints web del analizador."""

import base64
from io import BytesIO

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend.app import main as api


def image_bytes(is_leaf: bool = True) -> bytes:
    """Codifica una imagen PNG verde o una imagen sin region verde.

    Args:
        is_leaf: Si es verdadero, dibuja una region que debe detectarse.

    Returns:
        Contenido PNG adecuado para enviarlo a la API de pruebas.
    """
    image = Image.new("RGB", (240, 180), (235, 230, 215))
    if is_leaf:
        ImageDraw.Draw(image).ellipse((65, 35, 175, 145), fill=(40, 145, 55))
    else:
        image = Image.new("RGB", (240, 180), (180, 90, 35))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_health_and_frontend_are_available() -> None:
    """Confirma que el estado de API y la pagina principal respondan."""
    client = TestClient(api.app)

    assert client.get("/api/health").json() == {"status": "ok"}
    assert "Herbario visual" in client.get("/").text


def test_preview_is_small_and_preserves_binary_mask() -> None:
    """Reduce vistas RGB y conserva las mascaras en PNG sin perdida."""
    rgb_image = np.zeros((1200, 900, 3), dtype=np.uint8)
    rgb_url, rgb_extension = api.encode_preview(rgb_image, "original")
    rgb_bytes = base64.b64decode(rgb_url.split(",", maxsplit=1)[1])

    mask = np.zeros((1200, 900), dtype=np.uint8)
    mask_url, mask_extension = api.encode_preview(mask, "mascara_hsv")
    mask_bytes = base64.b64decode(mask_url.split(",", maxsplit=1)[1])

    assert rgb_extension == "jpg"
    assert Image.open(BytesIO(rgb_bytes)).size == (480, 640)
    assert mask_extension == "png"
    assert Image.open(BytesIO(mask_bytes)).size == (480, 640)


def test_analyze_upload_returns_named_stage_previews() -> None:
    """Devuelve etapas compactas con nombres adecuados para descarga."""
    client = TestClient(api.app)

    response = client.post(
        "/api/analyze",
        files=[
            ("files", ("hoja.png", image_bytes(), "image/png")),
            ("files", ("sin_hoja.png", image_bytes(False), "image/png")),
        ],
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert [result["status"] for result in results] == ["ok", "error"]
    result = results[0]
    assert result["status"] == "ok"
    assert result["measurements"]["area_px"] > 0
    assert [stage["key"] for stage in result["stages"]] == [
        "original",
        "mascara_hsv",
        "mascara_limpia",
        "contorno",
        "hoja_aislada",
    ]
    assert [stage["filename"] for stage in result["stages"]] == [
        "hoja_original.jpg",
        "hoja_mascara_hsv.png",
        "hoja_mascara_limpia.png",
        "hoja_contorno.jpg",
        "hoja_hoja_aislada.jpg",
    ]
    assert all(stage["image"].startswith("data:image/") for stage in result["stages"])


def test_analyze_reports_an_image_without_leaf() -> None:
    """Devuelve un error por archivo sin impedir la respuesta de la API."""
    client = TestClient(api.app)

    response = client.post(
        "/api/analyze",
        files=[("files", ("sin_hoja.png", image_bytes(False), "image/png"))],
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "error"
    assert "No se detecto" in response.json()["results"][0]["error"]
