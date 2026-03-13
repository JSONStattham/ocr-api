import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image
import pytesseract

app = FastAPI()

API_KEY = os.getenv("OCR_API_KEY", "")


def check_api_key(x_api_key: str | None):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ocr-image")
async def ocr_image(
    file: UploadFile = File(...),
    lang: str = Form("deu+eng"),
    psm: int = Form(6),
    x_api_key: str | None = Header(default=None),
):
    check_api_key(x_api_key)

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        text = pytesseract.image_to_string(
            image,
            lang=lang,
            config=f"--psm {psm}"
        )
        return JSONResponse({
            "type": "image",
            "text": text
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ocr-pdf")
async def ocr_pdf(
    file: UploadFile = File(...),
    lang: str = Form("deu+eng"),
    x_api_key: str | None = Header(default=None),
):
    check_api_key(x_api_key)

    filename = file.filename or "input.pdf"
    suffix = Path(filename).suffix.lower()

    if suffix != ".pdf" and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF allowed on /ocr-pdf")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    tmpdir = tempfile.mkdtemp(prefix="ocrpdf_")
    input_pdf = os.path.join(tmpdir, "input.pdf")
    output_pdf = os.path.join(tmpdir, "output.pdf")

    try:
        with open(input_pdf, "wb") as f:
            f.write(raw)

        cmd = [
            "ocrmypdf",
            "-l", lang,
            input_pdf,
            output_pdf,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail=result.stderr.strip() or "ocrmypdf failed"
            )

        return FileResponse(
            output_pdf,
            media_type="application/pdf",
            filename="output_searchable.pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pass
