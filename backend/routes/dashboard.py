from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint


def create_dashboard_blueprint(render_dashboard: Callable[[], Any]) -> Blueprint:
    blueprint = Blueprint("dashboard_routes", __name__)

    @blueprint.get("/dashboard")
    def dashboard():
        return render_dashboard()

    return blueprint
