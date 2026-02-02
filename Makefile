install:
	uv pip install -e ".[dev]"

run-app:
	flask --app main --debug run --port 8080
lint:
	uv run ruff check 
test:
	uv run pytest 