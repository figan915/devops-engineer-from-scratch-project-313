install:
	uv pip install -e ".[dev]"

run-app:
	uv run flask --app main --debug run --port 8080
lint:
	uv run ruff check 
test:
	uv run pytest
build:
	docker build -t flask-uv-app .
docker-run:
	docker run -p 8080:8080 flask-uv-app

# --- UI (dev) ---
# Выбор бэкенда (в этом проекте пока только Flask)
FRAMEWORK ?= flask

# Установка npm-зависимостей (создаст package.json при необходимости)
ui-init:
	@if [ ! -f package.json ]; then npm init -y; fi
	npm install @hexlet/project-devops-deploy-crud-frontend
	npm install --save-dev concurrently

# Запуск фронтенда (порт фиксированный 5173)
ui:
	npx start-hexlet-devops-deploy-crud-frontend

# Запуск бэкенда (порт 8080)
api:
	BASE_URL=http://localhost:8080 DATABASE_URL=sqlite:///./dev.db uv run flask --app main run --host 0.0.0.0 --port 8080

# Одновременный запуск фронта и бэка
# Запускать так: FRAMEWORK=flask make dev
# (Ожидается, что в package.json есть scripts: ui, api, dev)
dev:
	@if [ "$(FRAMEWORK)" = "flask" ]; then \
		npm run dev; \
	else \
		echo "Unknown FRAMEWORK=$(FRAMEWORK)"; exit 1; \
	fi