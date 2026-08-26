.PHONY: test coverage lint format typecheck check pre-commit clean check-setup setup

test:
	uv run pytest

test-fast:
	uv run pytest -m "not slow" -v

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

pre-commit:
	uv run pre-commit run --all-files

prep:
	git add --all
	-make pre-commit
	make pre-commit
	git add --all
	make typecheck
	make check

check: lint typecheck pre-commit test-fast

check-full: lint typecheck pre-commit test


clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
