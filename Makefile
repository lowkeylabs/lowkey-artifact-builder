.PHONY: test coverage lint format typecheck check pre-commit clean check-setup setup

test:
	uv run pytest

check-setup:
	uv run scripts/check_dependencies.py


setup:
	sudo apt install openscad
	sudo apt install inkscape
	sudo apt install nodejs
	sudo apt install npm


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
