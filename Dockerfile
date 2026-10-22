FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 DATA_DIR=/data PORT=8000
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY spam_agent ./spam_agent
COPY static ./static
COPY models ./models
COPY data/replay.csv.gz data/holdout.csv.gz ./data/
RUN useradd -m app && mkdir -p /data && chown app /data
USER app
VOLUME ["/data"]
EXPOSE 8000
# 512 MB of RAM is the practical minimum: measured 175 MB idle, ~370 MB peak while retraining.
HEALTHCHECK --interval=30s --timeout=4s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health',timeout=3)"
CMD ["sh", "-c", "uvicorn spam_agent.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
