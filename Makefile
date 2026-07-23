.PHONY: backend-install backend-test backend-lint backend-typecheck migrate up down frontend-install frontend-build frontend-test speech-install speech-test quality

backend-install:
	python -m pip install -e "backend[dev]"

backend-test:
	python -m pytest backend/tests

backend-lint:
	python -m ruff check backend

backend-typecheck:
	python -m mypy backend/app

migrate:
	cd backend && alembic upgrade head

up:
	docker compose up --build

down:
	docker compose down

frontend-install:
	cd frontend && npm ci

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm test -- --run

speech-install:
	python -m pip install -e "speech-ai[dev]"

speech-test:
	python -m pytest speech-ai/tests

quality: backend-test backend-lint backend-typecheck frontend-test frontend-build speech-test
