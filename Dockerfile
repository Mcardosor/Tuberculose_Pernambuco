FROM python:3.11-slim

WORKDIR /app

# Dependências Python primeiro, para aproveitar cache de layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY src/ src/

# Os dados (parquets, geojsons, agregados) entram por volume em produção —
# são gerados pelo ETL e não pertencem à imagem. Ver docker-compose.yml.

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/cenarios/tbpe/_stcore/health')"

CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.baseUrlPath=cenarios/tbpe", \
     "--server.fileWatcherType=none", \
     "--browser.gatherUsageStats=false"]
