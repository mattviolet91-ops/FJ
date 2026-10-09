# Image unique : interface compilée + API Python.
FROM node:22-slim AS interface
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MMT_DATA_DIR=/data MMT_FRONTEND_DIR=/app/frontend/dist
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core libexpat1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/mmt ./mmt
COPY --from=interface /app/dist /app/frontend/dist
RUN useradd -r -m -u 1000 mmt && mkdir -p /data && chown mmt /data
USER mmt
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/sante')"
CMD ["uvicorn", "mmt.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
