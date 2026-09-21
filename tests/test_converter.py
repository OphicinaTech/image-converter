from io import BytesIO

import pytest
from PIL import Image

from image_converter.converter import ConversionError, convert_image


def create_png(mode: str = "RGBA") -> bytes:
    image = Image.new(mode, (8, 8), (255, 0, 0, 128) if mode == "RGBA" else (255, 0, 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_png_to_webp_is_lossless() -> None:
    source = create_png()

    result = convert_image(source, "WEBP")

    with Image.open(BytesIO(result)) as converted:
        assert converted.format == "WEBP"
        assert converted.size == (8, 8)
        assert converted.mode == "RGBA"

        with Image.open(BytesIO(source)) as original:
            assert list(original.getdata()) == list(converted.getdata())


def test_png_to_avif_preserves_dimensions() -> None:
    source = create_png("RGB")

    result = convert_image(source, "AVIF")

    with Image.open(BytesIO(result)) as converted:
        assert converted.format == "AVIF"
        assert converted.size == (8, 8)


def test_unsupported_output_format_is_rejected() -> None:
    with pytest.raises(ConversionError):
        convert_image(create_png(), "JPEG")


def test_non_png_input_is_rejected() -> None:
    image = Image.new("RGB", (4, 4), "red")
    output = BytesIO()
    image.save(output, format="JPEG")

    with pytest.raises(ConversionError):
        convert_image(output.getvalue(), "WEBP")
