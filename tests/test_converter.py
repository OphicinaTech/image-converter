from io import BytesIO

import pytest
from PIL import Image

from image_converter.converter import (
    MOBILE_MAX_EDGE,
    ConversionError,
    convert_image,
)


def create_image(fmt: str = "PNG", mode: str = "RGBA", size: tuple[int, int] = (8, 8)) -> bytes:
    color = (255, 0, 0, 128) if mode == "RGBA" else (255, 0, 0)
    image = Image.new(mode, size, color)
    output = BytesIO()
    image.save(output, format=fmt)
    return output.getvalue()


def test_png_to_webp_is_lossless() -> None:
    source = create_image()

    result = convert_image(source, "WEBP")

    with Image.open(BytesIO(result)) as converted:
        assert converted.format == "WEBP"
        assert converted.size == (8, 8)
        assert converted.mode == "RGBA"

        with Image.open(BytesIO(source)) as original:
            assert list(original.getdata()) == list(converted.getdata())


def test_png_to_avif_preserves_dimensions() -> None:
    source = create_image("PNG", "RGB")

    result = convert_image(source, "AVIF")

    with Image.open(BytesIO(result)) as converted:
        assert converted.format == "AVIF"
        assert converted.size == (8, 8)


def test_webp_input_can_be_reencoded() -> None:
    source = convert_image(create_image(), "WEBP")

    result = convert_image(source, "AVIF", "compact")

    with Image.open(BytesIO(result)) as converted:
        assert converted.format == "AVIF"
        assert converted.size == (8, 8)


def test_mobile_preset_downscales_long_edge() -> None:
    source = create_image("PNG", "RGB", (MOBILE_MAX_EDGE + 400, 900))

    result = convert_image(source, "WEBP", "mobile")

    with Image.open(BytesIO(result)) as converted:
        assert converted.format == "WEBP"
        assert converted.size[0] == MOBILE_MAX_EDGE
        assert converted.size[1] < 900


def test_mobile_preset_keeps_small_images() -> None:
    source = create_image("PNG", "RGB", (320, 240))

    result = convert_image(source, "WEBP", "mobile")

    with Image.open(BytesIO(result)) as converted:
        assert converted.size == (320, 240)


def test_unsupported_output_format_is_rejected() -> None:
    with pytest.raises(ConversionError):
        convert_image(create_image(), "JPEG")


def test_unsupported_preset_is_rejected() -> None:
    with pytest.raises(ConversionError):
        convert_image(create_image(), "WEBP", "ultra")


def test_non_png_jpeg_input_is_rejected() -> None:
    image = Image.new("RGB", (4, 4), "red")
    output = BytesIO()
    image.save(output, format="JPEG")

    with pytest.raises(ConversionError):
        convert_image(output.getvalue(), "WEBP")
