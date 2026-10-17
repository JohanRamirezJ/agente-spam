FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 DATA_DIR=/data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY spam_agent ./spam_agent
COPY static ./static
COPY models/model.joblib ./models/model.joblib
COPY data/replay.csv.gz data/holdout.csv.gz ./data/
RUN useradd -m app && mkdir -p /data && chown app /data
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn spam_agent.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
