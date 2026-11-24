"""Carga y guardado de imagenes con Pillow."""

import re
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidImageError(ValueError):
    """Indica que los bytes o la ruta no contienen una imagen legible."""


def load_image(source: bytes | Path, max_pixels: int | None = None) -> Image.Image:
    """Abre una imagen y la devuelve orientada y convertida a RGB.

    Args:
        source: Bytes de una carga web o ruta de archivo local.
        max_pixels: Maximo de pixeles permitido; None deja el tamano sin limitar.

    Returns:
        Imagen Pillow en modo RGB con la orientacion EXIF aplicada.

    Raises:
        InvalidImageError: Si Pillow no puede abrir o decodificar la imagen.
    """
    try:
        image_source = Image.open(BytesIO(source) if isinstance(source, bytes) else source)
        if max_pixels is not None and image_source.width * image_source.height > max_pixels:
            raise InvalidImageError(
                f"La imagen supera el maximo permitido de {max_pixels:,} pixeles."
            )
        image_source.load()
        return ImageOps.exif_transpose(image_source).convert("RGB")
    except InvalidImageError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as error:
        raise InvalidImageError("El archivo no contiene una imagen valida.") from error


def safe_stem(filename: str) -> str:
    """Normaliza el nombre de archivo para usarlo en las salidas.

    Args:
        filename: Nombre original recibido desde el sistema o el navegador.

    Returns:
        Nombre base sin ruta ni caracteres especiales.
    """
    basename = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    stem = Path(basename).stem
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return normalized or "imagen"


def save_stages(
    stages: dict[str, np.ndarray], output_dir: Path, image_name: str
) -> list[Path]:
    """Guarda cada etapa del analisis como archivo PNG descriptivo.

    Args:
        stages: Imagenes RGB o mascaras en escala de grises por etapa.
        output_dir: Carpeta donde se escribiran los PNG.
        image_name: Prefijo seguro para los nombres generados.

    Returns:
        Rutas de todos los archivos PNG guardados.

    Raises:
        OSError: Si no se puede crear la carpeta o escribir algun archivo.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = safe_stem(image_name)
    saved_files: list[Path] = []
    for stage_name, array in stages.items():
        file_path = output_dir / f"{prefix}_{stage_name}.png"
        Image.fromarray(array).save(file_path, format="PNG")
        saved_files.append(file_path)
    return saved_files
