FROM python:3.12-slim
WORKDIR /workspace/api
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ ./
COPY engine/ /workspace/engine/
COPY examples/ /workspace/examples/
COPY infra/scripts/ /workspace/infra/scripts/
ENV PYTHONPATH=/workspace/api:/workspace
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
