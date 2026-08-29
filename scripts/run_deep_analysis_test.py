"""Script de prueba para build_deep_analysis(9).

Corre desde la raíz del proyecto con:
    python scripts/run_deep_analysis_test.py

Imprime el JSON completo en stdout para comparar con el análisis de referencia.
No persiste en DB (persist=False).
"""
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env.local", override=True)

from intelligence.curriculum_deep_analysis_engine import build_deep_analysis  # noqa: E402

if __name__ == "__main__":
    spec_id = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    print(f"[test] Running build_deep_analysis({spec_id}) — persist=False …\n")
    result = build_deep_analysis(spec_id, persist=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
