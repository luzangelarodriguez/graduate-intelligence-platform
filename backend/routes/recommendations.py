from __future__ import annotations

from flask import Blueprint, jsonify


def create_recommendations_blueprint() -> Blueprint:
    blueprint = Blueprint("recommendations_routes", __name__, url_prefix="/api/recommendations")

    @blueprint.get("/health")
    def health():
        return jsonify({"status": "ready", "module": "recommendations"})

    return blueprint
