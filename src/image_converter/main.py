from __future__ import annotations

from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .converter import (
    SUPPORTED_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS,
    ConversionError,
    convert_image,
)

app = FastAPI(
    title="Image Converter",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

# Caminho para a raiz do projeto (image-converter/)
# Path(__file__) -> .../src/image_converter/main.py
# .parent.parent.parent -> .../image-converter
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Monta os diretórios de static e templates apontando para a raiz
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
templates = Jinja2Templates(directory=ROOT_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/convert")
async def convert(
    request: Request,
    output_format: str,
) -> Response:
    """Convert one image received as a raw request body."""

    target = output_format.upper()
    if target not in SUPPORTED_OUTPUT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported output format. Use one of: {sorted(SUPPORTED_OUTPUT_FORMATS)}",
        )

    relative_path = request.headers.get("X-Relative-Path", "")
    safe_path = _validate_relative_path(relative_path)

    source = await request.body()
    if not source:
        raise HTTPException(status_code=400, detail="Empty image payload.")

    try:
        result = convert_image(source, target)
    except ConversionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ext = target.lower()
    output_name = safe_path.with_suffix(f".{ext}").name

    # Ajusta o media_type correto para o header HTTP (ex: JPG -> image/jpeg)
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    return Response(
        content=result,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{output_name}"',
            "X-Input-Format": "PNG",
        },
    )


def _validate_relative_path(value: str) -> PurePosixPath:
    """Validate a browser-provided relative path.

    The path is only used to identify the output filename to the client.
    It is never used by the server as a filesystem path.
    """

    normalized = value.replace("\\", "/").strip("/")
    path = PurePosixPath(normalized)

    if not normalized or path.is_absolute() or ".." in path.parts:
        raise HTTPException(status_code=400, detail="Invalid relative path.")

    if path.suffix.lower() != ".png":
        raise HTTPException(
            status_code=400,
            detail=f"Only PNG inputs are supported. Allowed: {sorted(SUPPORTED_INPUT_FORMATS)}",
        )

    return path