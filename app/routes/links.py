# app/routes/links.py

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from app.db import get_session

# ВАЖНО: на этом этапе модель Link живёт в main.py, поэтому импортируем её оттуда.
# Позже вынесем модель в app/models.py и тогда импорт будет: from app.models import Link
from app.models import Link

bp = Blueprint("links", __name__)


@bp.get("/api/links")
def list_links():
    """Возвращает список всех коротких ссылок."""
    base = current_app.config["BASE_URL"].rstrip("/")

    with get_session() as session:
        statement = select(Link)
        links = session.exec(statement).all()

    return (
        jsonify(
            [
                {
                    "id": link.id,
                    "original_url": link.original_url,
                    "short_name": link.short_name,
                    "short_url": f"{base}/r/{link.short_name}",
                }
                for link in links
            ]
        ),
        200,
    )


@bp.get("/api/links/<int:link_id>")
def get_link(link_id: int):
    """Возвращает одну ссылку по id."""
    base = current_app.config["BASE_URL"].rstrip("/")

    with get_session() as session:
        statement = select(Link).where(Link.id == link_id)
        link = session.exec(statement).first()

    if link is None:
        return jsonify({"error": "link not found"}), 404

    return (
        jsonify(
            {
                "id": link.id,
                "original_url": link.original_url,
                "short_name": link.short_name,
                "short_url": f"{base}/r/{link.short_name}",
            }
        ),
        200,
    )

@bp.post("/api/links")
def create_link():
    """Создаёт новую короткую ссылку.

    Успех: 201 + объект ссылки
    Конфликт short_name: 409 + {"error": "short_name already exists"}
    Невалидный запрос: 400 + {"error": "invalid payload"}
    """
    payload = request.get_json(silent=True)
    if not payload or "original_url" not in payload or "short_name" not in payload:
        return jsonify({"error": "invalid payload"}), 400

    link = Link(
        short_name=payload["short_name"],
        original_url=payload["original_url"],
    )

    # Достаём engine, созданный в create_app(), из конфига приложения
    engine = current_app.config["DB_ENGINE"]

    try:
        with get_session() as session:
            session.add(link)
            session.commit()
            session.refresh(link)
    except IntegrityError:
        # UNIQUE-конфликт по short_name
        return jsonify({"error": "short_name already exists"}), 409

    # short_url не храним в БД — формируем на лету из BASE_URL и short_name
    base = current_app.config["BASE_URL"].rstrip("/")
    return (
        jsonify(
            {
                "id": link.id,
                "original_url": link.original_url,
                "short_name": link.short_name,
                "short_url": f"{base}/r/{link.short_name}",
            }
        ),
        201,
    )


@bp.delete("/api/links/<int:link_id>")
def delete_link(link_id: int):
    """Удаляет ссылку по id."""
    with get_session() as session:
        statement = select(Link).where(Link.id == link_id)
        link = session.exec(statement).first()

        if link is None:
            return jsonify({"error": "link not found"}), 404

        session.delete(link)
        session.commit()

    # 204 должен быть без тела
    return "", 204


@bp.put("/api/links/<int:link_id>")
def update_link(link_id: int):
    """Обновляет ссылку по id."""
    payload = request.get_json(silent=True)
    if not payload or "original_url" not in payload or "short_name" not in payload:
        return jsonify({"error": "invalid payload"}), 400

    with get_session() as session:
        statement = select(Link).where(Link.id == link_id)
        link = session.exec(statement).first()

        if link is None:
            return jsonify({"error": "link not found"}), 404

        link.original_url = payload["original_url"]
        link.short_name = payload["short_name"]

        try:
            session.add(link)
            session.commit()
            session.refresh(link)
        except IntegrityError:
            return jsonify({"error": "short_name already exists"}), 409

    base = current_app.config["BASE_URL"].rstrip("/")
    return (
        jsonify(
            {
                "id": link.id,
                "original_url": link.original_url,
                "short_name": link.short_name,
                "short_url": f"{base}/r/{link.short_name}",
            }
        ),
        200,
    )

