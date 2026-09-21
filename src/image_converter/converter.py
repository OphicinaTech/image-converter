from __future__ import annotations

from io import BytesIO
from typing import Final

from PIL import Image

SUPPORTED_INPUT_FORMATS: Final[frozenset[str]] = frozenset({"PNG"})
SUPPORTED_OUTPUT_FORMATS: Final[frozenset[str]] = frozenset({"WEBP", "AVIF"})


class ConversionError(ValueError):
    """Raised when an image cannot be converted with the requested settings."""


def convert_image(source: bytes, output_format: str) -> bytes:
    """Convert an image without resizing it.

    WebP is encoded losslessly.
    AVIF uses maximum quality and 4:4:4 chroma sampling.
    """

    target = output_format.upper()

    if target not in SUPPORTED_OUTPUT_FORMATS:
        raise ConversionError(f"Unsupported output format: {output_format}")

    try:
        with Image.open(BytesIO(source)) as image:
            if image.format not in SUPPORTED_INPUT_FORMATS:
                raise ConversionError(
                    f"Unsupported input format: {image.format or 'unknown'}"
                )

            image.load()
            save_options = _build_save_options(image, target)

            output = BytesIO()
            image.save(output, format=target, **save_options)
            return output.getvalue()

    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Unable to convert image: {exc}") from exc


def _build_save_options(image: Image.Image, target: str) -> dict[str, object]:
    """Build encoder options while preserving supported metadata."""

    options: dict[str, object] = {}

    icc_profile = image.info.get("icc_profile")
    if icc_profile:
        options["icc_profile"] = icc_profile

    exif = image.info.get("exif")
    if exif:
        options["exif"] = exif

    xmp = image.info.get("xmp")
    if xmp:
        options["xmp"] = xmp

    if target == "WEBP":
        options.update(
            lossless=True,
            quality=100,
            method=6,
            exact=True,
        )
    else:
        options.update(
            quality=100,
            subsampling="4:4:4",
            speed=6,
        )

    return options
