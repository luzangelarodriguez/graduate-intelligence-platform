from __future__ import annotations

import argparse
import json
from pathlib import Path

from sync_to_railway import connect, get_railway_config, load_dotenv_files


ROOT = Path(__file__).resolve().parent


def apply_migrations(files: list[str], dry_run: bool) -> dict[str, object]:
    config = get_railway_config()
    applied: list[str] = []
    with connect(config) as conn:
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                for file_name in files:
                    path = ROOT / file_name
                    if not path.exists():
                        raise FileNotFoundError(path)
                    sql = path.read_text(encoding="utf-8")
                    cur.execute(sql)
                    applied.append(file_name)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"dry_run": dry_run, "applied": applied}


def main() -> int:
    load_dotenv_files()
    parser = argparse.ArgumentParser(description="Aplica migraciones SQL idempotentes en Railway.")
    parser.add_argument("files", nargs="+", help="Rutas relativas de migraciones SQL.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = apply_migrations(args.files, args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

