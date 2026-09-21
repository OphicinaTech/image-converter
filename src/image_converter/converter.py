from __future__ import annotations

from io import BytesIO
from typing import Final

from PIL import Image

SUPPORTED_INPUT_FORMATS: Final[frozenset[str]] = frozenset({"PNG", "WEBP", "AVIF"})
SUPPORTED_OUTPUT_FORMATS: Final[frozenset[str]] = frozenset({"WEBP", "AVIF"})
SUPPORTED_INPUT_EXTENSIONS: Final[frozenset[str]] = frozenset({".png", ".webp", ".avif"})
SUPPORTED_PRESETS: Final[frozenset[str]] = frozenset({"lossless", "compact", "mobile"})
MOBILE_MAX_EDGE: Final[int] = 1600


class ConversionError(ValueError):
    """Raised when an image cannot be converted with the requested settings."""


def convert_image(
    source: bytes,
    output_format: str,
    preset: str = "lossless",
) -> bytes:
    """Convert an image according to the selected output format and preset.

    lossless: same pixels and dimensions (WebP lossless; AVIF at quality 100).
    compact: visually high quality, lossy, original dimensions.
    mobile: longest edge capped at 1600px, lossy, aimed at KB-range files.
    """

    target = output_format.upper()
    mode = preset.lower()

    if target not in SUPPORTED_OUTPUT_FORMATS:
        raise ConversionError(f"Unsupported output format: {output_format}")

    if mode not in SUPPORTED_PRESETS:
        raise ConversionError(f"Unsupported preset: {preset}")

    try:
        with Image.open(BytesIO(source)) as image:
            if image.format not in SUPPORTED_INPUT_FORMATS:
                raise ConversionError(
                    f"Unsupported input format: {image.format or 'unknown'}"
                )

            image.load()
            working = image.copy()

            if mode == "mobile":
                working = _fit_max_edge(working, MOBILE_MAX_EDGE)

            working = _normalize_mode(working, target)
            save_options = _build_save_options(image, target, mode)

            output = BytesIO()
            working.save(output, format=target, **save_options)
            return output.getvalue()

    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Unable to convert image: {exc}") from exc


def _fit_max_edge(image: Image.Image, max_edge: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_edge:
        return image

    scale = max_edge / longest
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _normalize_mode(image: Image.Image, target: str) -> Image.Image:
    if image.mode in {"RGB", "RGBA"}:
        return image

    if image.mode in {"LA", "PA", "P"} and "transparency" in image.info:
        return image.convert("RGBA")

    if image.mode == "P":
        return image.convert("RGB")

    if image.mode in {"1", "L", "CMYK", "YCbCr", "LAB", "HSV", "I", "F"}:
        return image.convert("RGB")

    if target == "WEBP" and image.mode == "RGBA":
        return image

    return image.convert("RGB")


def _build_save_options(
    image: Image.Image,
    target: str,
    preset: str,
) -> dict[str, object]:
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
        if preset == "lossless":
            # method=4 is much faster than 6; quality still means compression
            # effort for lossless WebP, not visual quality.
            options.update(lossless=True, quality=100, method=4, exact=True)
        elif preset == "compact":
            options.update(lossless=False, quality=82, method=4, exact=False)
        else:
            options.update(lossless=False, quality=72, method=4, exact=False)
        return options

    if preset == "lossless":
        options.update(quality=100, subsampling="4:4:4", speed=8, max_threads=2)
    elif preset == "compact":
        options.update(quality=62, subsampling="4:2:0", speed=6, max_threads=2)
    else:
        options.update(quality=48, subsampling="4:2:0", speed=6, max_threads=2)

    return options
