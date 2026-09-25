FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY app /app/app

RUN useradd --create-home --uid 10002 boneqc-ai \
    && chown -R boneqc-ai:boneqc-ai /app

USER boneqc-ai

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
