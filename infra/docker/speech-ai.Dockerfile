FROM python:3.12-slim

WORKDIR /workspace/speech-ai
COPY speech-ai/pyproject.toml ./pyproject.toml
COPY speech-ai/app ./app
RUN pip install --no-cache-dir -e .

