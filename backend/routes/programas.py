from __future__ import annotations

from flask import Blueprint, jsonify

from backend.services.dashboard_service import list_programs_base


def create_programas_blueprint(db_name: str | None = None) -> Blueprint:
    blueprint = Blueprint("programas_routes", __name__, url_prefix="/api/programas")

    @blueprint.get("")
    def list_programas():
        return jsonify(list_programs_base(db_name=db_name))

    return blueprint
