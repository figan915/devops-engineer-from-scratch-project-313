# app/routes/links.py

import json

from flask import Blueprint, abort, current_app, jsonify, make_response, redirect, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.db import get_session
from app.models import Link

bp = Blueprint("links", __name__)



def _validation_error(details: list[dict]):
    # Hexlet checker (vitest) expects 422 with {"detail": [...]} like FastAPI
    return jsonify({"detail": details}), 422


def _not_found_error():
    return jsonify({"detail": "link not found"}), 404


def _parse_and_validate_payload(required: bool = True):
    """Validate incoming JSON body to match external contract tests.

    - Missing required fields -> 422 with detail array
    - Wrong types -> 422 with detail array
    """
    if not request.is_json:
        return None, _validation_error(
            [
                {
                    "loc": ["body"],
                    "msg": "Invalid JSON",
                    "type": "json_invalid",
                }
            ]
        )

    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return None, _validation_error(
            [
                {
                    "loc": ["body"],
                    "msg": "Invalid JSON",
                    "type": "json_invalid",
                }
            ]
        )

    errors: list[dict] = []

    if required:
        if "original_url" not in payload:
            errors.append(
                {
                    "loc": ["body", "original_url"],
                    "msg": "Field required",
                    "type": "missing",
                }
            )
        if "short_name" not in payload:
            errors.append(
                {
                    "loc": ["body", "short_name"],
                    "msg": "Field required",
                    "type": "missing",
                }
            )

    if "original_url" in payload and not isinstance(payload["original_url"], str):
        errors.append(
            {
                "loc": ["body", "original_url"],
                "msg": "Input should be a valid string",
                "type": "string_type",
            }
        )

    if "short_name" in payload and not isinstance(payload["short_name"], str):
        errors.append(
            {
                "loc": ["body", "short_name"],
                "msg": "Input should be a valid string",
                "type": "string_type",
            }
        )

    if errors:
        return None, _validation_error(errors)

    return payload, None


@bp.get("/api/links")
def list_links():
    """Возвращает список коротких ссылок.

    Поддерживает пагинацию через query-параметр:
        /api/links?range=[0,10]

    Важно: трактуем диапазон как [start, end) (end НЕ включается),
    чтобы "10 элементов" соответствовало 0–9 (как в подсказке ТЗ).

    Ответ всегда массив объектов, плюс заголовок Content-Range:
        Content-Range: links <from>-<to>/<total>
    """
    base = current_app.config["BASE_URL"].rstrip("/")

    range_raw = request.args.get("range")

    # По умолчанию — без range отдаём всё
    start = 0
    end = None

    if range_raw is not None:
        try:
            start, end = json.loads(range_raw)
            start = int(start)
            end = int(end)
            if start < 0 or end < 0 or start > end:
                raise ValueError("invalid bounds")
        except Exception:
            return jsonify({"error": "Invalid range. Example: range=[0,10]"}), 400

    with get_session() as session:
        total = session.exec(select(func.count()).select_from(Link)).one()

        stmt = select(Link).order_by(Link.id)
        if range_raw is not None:
            limit = end - start  # end — exclusive
            stmt = stmt.offset(start).limit(limit)

        links = session.exec(stmt).all()

    data = [
        {
            "id": link.id,
            "original_url": link.original_url,
            "short_name": link.short_name,
            "short_url": f"{base}/r/{link.short_name}",
        }
        for link in links
    ]

    # Формируем Content-Range по реально возвращённым данным
    if total == 0:
        content_range = "links 0-0/0"
    elif len(data) == 0:
        # Диапазон ушёл за пределы данных
        content_range = f"links {start}-{start - 1}/{total}"
    else:
        content_range = f"links {start}-{start + len(data) - 1}/{total}"

    resp = make_response(jsonify(data), 200)
    resp.headers["Content-Range"] = content_range
    resp.headers["Accept-Ranges"] = "links"
    return resp


@bp.get("/api/links/<int:link_id>")
def get_link(link_id: int):
    """Возвращает одну ссылку по id."""
    base = current_app.config["BASE_URL"].rstrip("/")

    with get_session() as session:
        statement = select(Link).where(Link.id == link_id)
        link = session.exec(statement).first()

    if link is None:
        return _not_found_error()

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
    """Создаёт новую короткую ссылку."""
    payload, err = _parse_and_validate_payload(required=True)
    if err:
        return err

    link = Link(
        short_name=payload["short_name"],
        original_url=payload["original_url"],
    )

    try:
        with get_session() as session:
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
        201,
    )


@bp.delete("/api/links/<int:link_id>")
def delete_link(link_id: int):
    """Удаляет ссылку по id."""
    with get_session() as session:
        statement = select(Link).where(Link.id == link_id)
        link = session.exec(statement).first()

        if link is None:
            return _not_found_error()

        session.delete(link)
        session.commit()

    return "", 204


@bp.put("/api/links/<int:link_id>")
def update_link(link_id: int):
    """Обновляет ссылку по id."""
    payload, err = _parse_and_validate_payload(required=True)
    if err:
        return err

    with get_session() as session:
        statement = select(Link).where(Link.id == link_id)
        link = session.exec(statement).first()

        if link is None:
            return _not_found_error()

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


@bp.get("/r/<string:short_name>")
def redirect_short_link(short_name: str):
    """Редирект по короткому имени."""
    with get_session() as session:
        stmt = select(Link).where(Link.short_name == short_name)
        link = session.exec(stmt).first()

    if link is None:
        abort(404)

    return redirect(link.original_url, code=302)