import io
import os
import tempfile
import subprocess
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import JSONResponse
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

@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    lang: str = Form("deu+eng"),
    x_api_key: str | None = Header(default=None),
):
    check_api_key(x_api_key)

    filename = (file.filename or "upload").lower()
    suffix = Path(filename).suffix

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    # PDF Pfad
    if suffix == ".pdf" or file.content_type == "application/pdf":
        with tempfile.TemporaryDirectory() as td:
            input_pdf = os.path.join(td, "input.pdf")
            output_pdf = os.path.join(td, "output.pdf")
            sidecar_txt = os.path.join(td, "output.txt")

            with open(input_pdf, "wb") as f:
                f.write(raw)

            cmd = [
                "ocrmypdf",
                "--mode", "skip",
                "--sidecar", sidecar_txt,
                "--output-type", "pdf",
                "-l", lang,
                input_pdf,
                output_pdf,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise HTTPException(
                    status_code=400,
                    detail=result.stderr or "OCRmyPDF failed"
                )

            text = ""
            if os.path.exists(sidecar_txt):
                with open(sidecar_txt, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

            return JSONResponse({
                "type": "pdf",
                "text": text,
                "note": "Bei PDFs mit bereits vorhandenem Text ist der Sidecar-Text oft leer. Solche PDFs zuerst direkt in n8n auslesen."
            })

    # Bild Pfad
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        text = pytesseract.image_to_string(image, lang=lang, config="--psm 6")
        return {"type": "image", "text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
