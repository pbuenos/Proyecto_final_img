"""API HTTP y servidor estatico de la aplicacion web."""

import base64
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
from PIL import Image

from backend.leaflab.image_io import (
    InvalidImageError,
    load_image,
    safe_stem,
)
from backend.leaflab.processor import (
    LeafAnalyzer,
    LeafNotFoundError,
    ProcessingOptions,
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_DIR / "frontend"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
PREVIEW_MAX_SIDE = 640
STAGE_LABELS = {
    "original": "Imagen original",
    "mascara_hsv": "Mascara HSV",
    "mascara_limpia": "Mascara morfologica",
    "contorno": "Contorno y medidas",
    "hoja_aislada": "Hoja aislada",
}
COLOR_STAGES = {"original", "contorno", "hoja_aislada"}

app = FastAPI(
    title="Analizador de hojas",
    description="Segmentacion HSV, limpieza morfologica y medicion de contornos.",
    version="1.0.0",
)


@app.get("/api/health", tags=["estado"])
def health() -> dict[str, str]:
    """Indica si el backend esta disponible.

    Returns:
        Estado simple para que el frontend compruebe la conexion.
    """
    return {"status": "ok"}


def encode_preview(array: np.ndarray, stage_name: str) -> tuple[str, str]:
    """Codifica una etapa como vista previa compacta para el navegador.

    Args:
        array: Imagen RGB o mascara en escala de grises como arreglo NumPy.
        stage_name: Nombre de la etapa, usado para elegir el formato de salida.

    Returns:
        Tupla con la URL de datos y la extension adecuada para descarga.
    """
    image = Image.fromarray(array)
    image.thumbnail(
        (PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE),
        Image.Resampling.LANCZOS,
    )
    buffer = BytesIO()
    if stage_name in COLOR_STAGES:
        image.save(buffer, format="JPEG", quality=82, optimize=True)
        media_type, extension = "image/jpeg", "jpg"
    else:
        image.save(buffer, format="PNG", optimize=True)
        media_type, extension = "image/png", "png"
    data_url = (
        f"data:{media_type};base64,"
        + base64.b64encode(buffer.getvalue()).decode("ascii")
    )
    return data_url, extension


@app.post("/api/analyze", tags=["analisis"])
async def analyze_images(
    files: list[UploadFile] = File(..., description="Una o mas imagenes"),
    hue_min: int = Form(25, ge=0, le=179),
    hue_max: int = Form(100, ge=0, le=179),
    saturation_min: int = Form(35, ge=0, le=255),
    value_min: int = Form(30, ge=0, le=255),
    kernel_size: int = Form(5, ge=1, le=31),
    min_area_ratio: float = Form(0.01, ge=0, lt=1),
) -> JSONResponse:
    """Analiza imagenes y devuelve vistas previas descargables de cada etapa.

    Args:
        files: Imagenes seleccionadas desde el formulario web.
        hue_min: Limite inferior de tono HSV.
        hue_max: Limite superior de tono HSV.
        saturation_min: Saturacion minima HSV.
        value_min: Brillo minimo HSV.
        kernel_size: Lado impar del kernel de limpieza.
        min_area_ratio: Area minima de contorno respecto de la imagen.

    Returns:
        JSON con mediciones, imagenes de etapas y errores individuales.

    Raises:
        HTTPException: Si faltan imagenes o los parametros HSV se contradicen.
    """
    if not files:
        raise HTTPException(status_code=422, detail="Selecciona al menos una imagen.")
    try:
        options = ProcessingOptions(
            hue_min=hue_min,
            hue_max=hue_max,
            saturation_min=saturation_min,
            value_min=value_min,
            kernel_size=kernel_size,
            min_area_ratio=min_area_ratio,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    analyzer = LeafAnalyzer(options)
    results = []
    total_bytes = 0
    for upload in files:
        content = await upload.read(MAX_UPLOAD_BYTES + 1)
        total_bytes += len(content)
        if total_bytes > MAX_UPLOAD_BYTES:
            results.append(
                {
                    "filename": upload.filename or "imagen",
                    "status": "error",
                    "error": "El total de imagenes supera el limite de 10 MB por solicitud.",
                }
            )
            continue

        try:
            image = load_image(content, max_pixels=MAX_IMAGE_PIXELS)
            result = analyzer.analyze(image)
        except (InvalidImageError, LeafNotFoundError) as error:
            results.append(
                {
                    "filename": upload.filename or "imagen",
                    "status": "error",
                    "error": str(error),
                }
            )
            continue

        filename = upload.filename or "imagen"
        stage_data = []
        prefix = safe_stem(filename)
        for stage_name, array in result.stages.items():
            image_url, extension = encode_preview(array, stage_name)
            stage_data.append(
                {
                    "key": stage_name,
                    "label": STAGE_LABELS[stage_name],
                    "filename": f"{prefix}_{stage_name}.{extension}",
                    "image": image_url,
                }
            )
        measurements = result.measurements
        results.append(
            {
                "filename": filename,
                "status": "ok",
                "measurements": {
                    "area_px": round(measurements.area_px, 2),
                    "perimeter_px": round(measurements.perimeter_px, 2),
                    "width_px": measurements.width_px,
                    "height_px": measurements.height_px,
                    "aspect_ratio": round(measurements.aspect_ratio, 4),
                    "area_ratio": round(measurements.area_ratio, 4),
                },
                "stages": stage_data,
            }
        )
    return JSONResponse({"results": results})


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
