from __future__ import annotations

from flask import Blueprint, jsonify

from backend.repositories.empleos_repository import fetch_jobs_basic


def create_empleos_blueprint(db_name: str | None = None) -> Blueprint:
    blueprint = Blueprint("empleos_routes", __name__, url_prefix="/api/empleos")

    @blueprint.get("")
    def list_empleos():
        return jsonify(fetch_jobs_basic(db_name=db_name))

    return blueprint
