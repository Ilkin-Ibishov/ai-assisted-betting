FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p data reports

CMD ["sh", "-c", "python -m app.cli init-db && exec python -m uvicorn app.api:api --host 0.0.0.0 --port ${PORT:-8000}"]
