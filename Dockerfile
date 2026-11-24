FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VTF_DATASET_DIR=/app/samples/demo_suite

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY tests ./tests
COPY samples ./samples
COPY docs ./docs

RUN pip install --no-cache-dir -e . --no-deps

EXPOSE 8000

CMD ["sh", "-c", "pytest -v && vtf validate --dataset samples/demo_suite && vtf mutate"]
