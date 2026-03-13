FROM jbarlow83/ocrmypdf-alpine:17.3.0

RUN python -m pip install --no-cache-dir fastapi uvicorn[standard] pillow pytesseract python-multipart

WORKDIR /app
COPY app.py /app/app.py

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
