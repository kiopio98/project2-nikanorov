.PHONY: install run lint test build

install:
	uv sync --locked

run:
	uv run database

lint:
	uv run ruff check .

test:
	uv run python tests/check_project.py

build:
	uv build
