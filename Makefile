.PHONY: test coverage lint format typecheck check pre-commit clean

test:
	uv run pytest

coverage:
	uv run pytest --cov=lowkey_artifact_builder --cov-report=term-missing

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck:
	uv run pyright

check: lint typecheck test

pre-commit:
	uv run pre-commit run --all-files

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
