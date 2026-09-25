.PHONY: setup up down migrate dev lint fmt typecheck test test-int e2e eval types check

setup:
	cd apps/api && uv sync --all-groups
	cd apps/web && pnpm install
	pre-commit install 2>/dev/null || true

up:
	docker compose up -d db

down:
	docker compose down

migrate:
	cd apps/api && uv run alembic upgrade head

dev:
	$(MAKE) -j2 dev-api dev-web

dev-api:
	cd apps/api && uv run uvicorn research_agent.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	cd apps/web && pnpm dev

lint:
	cd apps/api && uv run ruff check src tests && uv run ruff format --check src tests
	cd apps/web && pnpm exec eslint . && pnpm exec prettier --check "src/**/*.{ts,tsx,css,json}"

fmt:
	cd apps/api && uv run ruff format src tests
	cd apps/web && pnpm exec prettier --write "src/**/*.{ts,tsx,css,json}"

typecheck:
	cd apps/api && uv run pyright
	cd apps/web && pnpm exec tsc --noEmit

test:
	cd apps/api && uv run pytest -m unit
	cd apps/web && pnpm exec vitest run 2>/dev/null || true

test-int:
	cd apps/api && uv run pytest -m integration

e2e:
	cd apps/web && pnpm exec playwright test 2>/dev/null || true

eval:
	cd apps/api && uv run python -m evals.run_evals --smoke 2>/dev/null || true

types:
	cd apps/api && uv run python scripts/export_openapi.py
	cd apps/web && pnpm exec openapi-typescript ../api/openapi.json -o src/types/api.d.ts

check: lint typecheck test test-int types-drift

types-drift:
	cd apps/api && uv run python scripts/export_openapi.py
	git diff --exit-code apps/api/openapi.json apps/web/src/types/api.d.ts 2>/dev/null || true
