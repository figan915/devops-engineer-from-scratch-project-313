import os

from flask import Flask

from app.db import init_db


def create_app(*, testing: bool = False) -> Flask:
    """Фабрика приложения.

    - В режиме production/dev переменные окружения DATABASE_URL и BASE_URL обязательны.
    - В режиме тестирования используем SQLite in-memory, чтобы тесты были быстрыми и изолированными.
      BASE_URL в тестах можно брать из env или использовать дефолт.
    """

    app = Flask(__name__)

    # --- Конфигурация приложения (env) ---
    if testing:
        # В тестах не хотим зависеть от внешней БД — используем in-memory SQLite
        database_url = "sqlite:///:memory:"
        # Для тестов допускаем дефолт, чтобы не падать без BASE_URL
        base_url = os.getenv("BASE_URL", "http://localhost:8080")
    else:
        # В обычном режиме строго требуем DATABASE_URL (как в ТЗ)
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is required. Example: postgres://postgres:password@db:5432/appdb?sslmode=disable"
            )

        # Нормализация для совместимости: некоторые окружения (в т.ч. чекеры/платформы)
        # могут передавать DSN как postgres://..., а SQLAlchemy ожидает postgresql://...
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        # BASE_URL нужен, чтобы формировать short_url в ответах
        base_url = os.getenv("BASE_URL")
        if not base_url:
            raise RuntimeError("BASE_URL is required. Example: BASE_URL=https://short.io")

    # Сохраняем BASE_URL в конфиг приложения, чтобы не дергать os.getenv() по всему коду
    app.config["BASE_URL"] = base_url

    # --- Инициализация БД (идемпотентно: повторный запуск не ломает таблицы) ---
    init_db(app, database_url)

    # --- Роуты (пока базовый каркас) ---
    @app.route("/")
    def index():
        return "Введите localhost:8080/ping и получи ответ"

    @app.get("/ping")
    def get_ping():
        return "pong"

    from app.routes.links import bp as links_bp

    app.register_blueprint(links_bp)

    # Оставляем текущий контракт 404 для существующих тестов
    @app.errorhandler(404)
    def not_found(error):
        return "Page Not Found", 404

    return app


if __name__ == "__main__":
    # Ручной запуск для локальной разработки
    app = create_app(testing=False)
    app.run(host="127.0.0.1", port=8000, debug=True)