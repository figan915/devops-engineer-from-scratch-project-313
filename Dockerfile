# =========================
# 1️⃣ Stage: UI (готовая статика из npm-пакета)
# =========================
FROM node:20-alpine AS ui

WORKDIR /ui

# Пакет уже содержит собранный фронтенд (dist)
RUN npm init -y \
    && npm install @hexlet/project-devops-deploy-crud-frontend

# Копируем dist в отдельную директорию, которую потом заберём в финальный образ
RUN mkdir -p /public \
    && cp -r ./node_modules/@hexlet/project-devops-deploy-crud-frontend/dist/. /public/


# =========================
# 2️⃣ Stage: Backend + Nginx
# =========================
FROM python:3.14-slim

# =========================
# 2️⃣.1 Установка системных зависимостей
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nginx \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# =========================
# 2️⃣.2 Рабочая директория
# =========================
WORKDIR /app

# Фиксируем путь виртуального окружения uv (иначе uv может создать .venv в другом месте)
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Используем python/flask из виртуального окружения uv
ENV PATH="/app/.venv/bin:$PATH"

# =========================
# 2️⃣.3 Копируем только файлы зависимостей для кэширования слоёв
# =========================
COPY pyproject.toml uv.lock ./

# =========================
# 2️⃣.4 Установка uv и зависимостей
# =========================
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

# =========================
# 2️⃣.5 Копируем весь проект
# =========================
COPY . .

# =========================
# 2️⃣.6 Кладём UI-статику в /app/public
# =========================
RUN mkdir -p /app/public
COPY --from=ui /public/ /app/public/

# =========================
# 2️⃣.7 Конфиг Nginx: раздача статики + proxy /api/* и /r/*
# =========================
RUN rm -f /etc/nginx/sites-enabled/default \
    && rm -f /etc/nginx/conf.d/default.conf \
    && printf '%s\n' \
'server {' \
'  listen 80;' \
'  server_name _;' \
'' \
'  root /app/public;' \
'  index index.html;' \
'' \
'  # UI (SPA): любые пути (кроме /api и /r) отдаём index.html' \
'  location / {' \
'    try_files $uri $uri/ /index.html;' \
'  }' \
'' \
'  # API проксируем в бэкенд' \
'  location /api/ {' \
'    proxy_pass http://127.0.0.1:8080;' \
'    proxy_set_header Host $host;' \
'    proxy_set_header X-Real-IP $remote_addr;' \
'    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'    proxy_set_header X-Forwarded-Proto $scheme;' \
'  }' \
'' \
'  # Редиректы по коротким ссылкам тоже проксируем в бэкенд' \
'  location /r/ {' \
'    proxy_pass http://127.0.0.1:8080;' \
'    proxy_set_header Host $host;' \
'    proxy_set_header X-Real-IP $remote_addr;' \
'    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
'    proxy_set_header X-Forwarded-Proto $scheme;' \
'  }' \
'}' \
> /etc/nginx/conf.d/app.conf

# =========================
# 2️⃣.8 Переменные окружения для Flask
# =========================
ENV FLASK_APP=main
ENV FLASK_ENV=production

# =========================
# 2️⃣.9 Порт контейнера (Render просит PORT=80)
# =========================
EXPOSE 80

# =========================
# 2️⃣.🔟 Команда по умолчанию
# Запускаем Flask на 127.0.0.1:8080 (внутри контейнера),
# а Nginx слушает 0.0.0.0:80 и проксирует запросы.
# =========================
CMD ["sh", "-lc", "uv run flask --app main run --host 127.0.0.1 --port 8080 & nginx -g 'daemon off;' "]