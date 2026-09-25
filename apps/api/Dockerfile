FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY app /app/app
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

RUN useradd --create-home --uid 10001 boneqc \
    && chown -R boneqc:boneqc /app

USER boneqc

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
