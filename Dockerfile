# Haushaltskasse-Dashboard — Container-Image (für Azure Container Apps oder App Service Container).
# Für "App Service (Code)" wird dieses Dockerfile NICHT gebraucht; dort genügt der Startbefehl
# (siehe haushaltskasse/docs/DEPLOY.md).
FROM python:3.12-slim

WORKDIR /app

# Nur requirements zuerst -> besserer Layer-Cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Azure setzt PORT zur Laufzeit; lokal 8000 als Default.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn haushaltskasse.dashboard.app:app --host 0.0.0.0 --port ${PORT}"]
