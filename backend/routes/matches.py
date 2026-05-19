from __future__ import annotations

from flask import Blueprint, jsonify

from backend.repositories.matches_repository import match_relation_name


def create_matches_blueprint(db_name: str | None = None) -> Blueprint:
    blueprint = Blueprint("matches_routes", __name__, url_prefix="/api/matches")

    @blueprint.get("/status")
    def status():
        return jsonify({"relation": match_relation_name(db_name=db_name)})

    return blueprint
