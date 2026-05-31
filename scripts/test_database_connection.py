from __future__ import annotations

from backend.database_config import test_connection


def main() -> None:
    diagnostics = test_connection()
    print("Connection successful")
    print(f"Database source: {diagnostics['mode']}")
    print(f"Tables found: {diagnostics['tables_found']}")


if __name__ == "__main__":
    main()
