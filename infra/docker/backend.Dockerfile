FROM python:3.12-slim

WORKDIR /workspace/backend
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
RUN pip install --no-cache-dir -e .

