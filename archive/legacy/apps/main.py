from __future__ import annotations

from flask import Flask

app = Flask(__name__)

import unir_alumni_alerts_app  # noqa: E402,F401


if __name__ == "__main__":
    raise SystemExit("Run with gunicorn -w 4 -b 0.0.0.0:5000 main:app")