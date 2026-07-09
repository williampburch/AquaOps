FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system aquaops && adduser --system --ingroup aquaops aquaops

COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN pip install --upgrade pip && pip install .

RUN mkdir -p /app/data /app/media && chown -R aquaops:aquaops /app

EXPOSE 8000

USER aquaops

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
