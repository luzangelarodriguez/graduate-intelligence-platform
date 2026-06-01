from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.services import list_semantic_roles


def main() -> None:
    try:
        result = list_semantic_roles(limit=20, offset=0, role_family="Criminology")
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    except Exception as exc:
        print(type(exc).__name__, exc)
        raise


if __name__ == "__main__":
    main()
