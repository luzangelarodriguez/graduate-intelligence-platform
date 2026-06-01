from __future__ import annotations

import json
import time
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.services import get_program_summary


def main() -> None:
    start = time.time()
    result = get_program_summary(108)
    elapsed = round(time.time() - start, 2)
    print(json.dumps({"elapsed": elapsed, "result": result}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
