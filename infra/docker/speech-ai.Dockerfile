FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace/speech-ai
COPY speech-ai/pyproject.toml ./pyproject.toml
COPY speech-ai/app ./app
RUN pip install --no-cache-dir -e .

RUN addgroup --system app && adduser --system --ingroup app app
USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
