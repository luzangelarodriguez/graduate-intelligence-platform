"""
Regression tests for the AI-powered ingestion pipeline (scripts/ingest_program.py).

Marks:
  - Tests that require DB are skipped when RAILWAY_DATABASE_URL is absent.
  - Tests that use OpenAI use mocked responses from fixtures (no real API cost in CI).

Run:
    pytest tests/test_ingest_regresion.py -v
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

FIXTURES = Path(__file__).parent / "fixtures"
MOCK_RESPONSES = json.loads((FIXTURES / "mock_openai_responses.json").read_text(encoding="utf-8"))
SAMPLE_TEXT = (FIXTURES / "sample_marketing_block.txt").read_text(encoding="utf-8")

from scripts.ingest_program import (
    _CANONICAL_SKILLS,
    _normalize_text,
    normalize_skills,
    split_into_blocks,
    build_record,
    hash_block,
    print_preview,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _all_skills_flat(skills_dict: dict) -> list[str]:
    result = []
    for items in skills_dict.values():
        result.extend(items)
    return result


# ── TestNormalizacion ──────────────────────────────────────────────────────────

class TestNormalizacion(unittest.TestCase):

    def test_canonical_ecommerce_variants(self):
        for raw in ("ecommerce", "E-Commerce", "e commerce", "e-commerce"):
            norm = _normalize_text(raw)
            canonical = _CANONICAL_SKILLS.get(norm, raw)
            self.assertEqual(canonical, "E-Commerce", f"Failed for raw={raw!r}")

    def test_canonical_acronyms(self):
        cases = [("seo", "SEO"), ("roi", "ROI"), ("linkedin", "LinkedIn"),
                 ("kpi", "KPI"), ("sem", "SEM"), ("tiktok", "TikTok")]
        for raw, expected in cases:
            norm = _normalize_text(raw)
            canonical = _CANONICAL_SKILLS.get(norm, raw)
            self.assertEqual(canonical, expected, f"Failed for raw={raw!r}")

    def test_dedup_across_tipos(self):
        skills_with_dup = [
            {"nombre": "SEO", "tipo": "marketing"},
            {"nombre": "seo", "tipo": "herramienta"},  # duplicate, different tipo
        ]
        result = normalize_skills(skills_with_dup)
        all_skills = _all_skills_flat(result)
        lower_skills = [s.lower() for s in all_skills]
        self.assertEqual(len(lower_skills), len(set(lower_skills)),
                         f"Duplicates found: {all_skills}")


# ── TestPipelineMock ───────────────────────────────────────────────────────────

class TestPipelineMock(unittest.TestCase):

    def setUp(self):
        self.block1_response = MOCK_RESPONSES["block_1"]
        self.block2_response = MOCK_RESPONSES["block_2"]
        self.programa = "Pregrado en Marketing y Publicidad"
        self.domain = "marketing"

    def test_split_blocks(self):
        blocks = split_into_blocks(SAMPLE_TEXT, self.programa)
        self.assertEqual(len(blocks), 2,
                         f"Expected 2 blocks, got {len(blocks)}: {[b['block_text'][:40] for b in blocks]}")

    def test_build_record_comercio_electronico(self):
        blocks = split_into_blocks(SAMPLE_TEXT, self.programa)
        rec = build_record(
            blocks[0], self.block1_response,
            self.programa, self.domain, "sample.txt", "abc123"
        )
        self.assertEqual(rec["asignatura"], "Comercio Electrónico")
        self.assertEqual(len(rec["resultados_aprendizaje"]), 3)
        all_skills = _all_skills_flat(rec["skills"])
        self.assertIn("E-Commerce", all_skills, f"E-Commerce not in skills: {all_skills}")

    def test_build_record_marketing_digital(self):
        blocks = split_into_blocks(SAMPLE_TEXT, self.programa)
        rec = build_record(
            blocks[1], self.block2_response,
            self.programa, self.domain, "sample.txt", "abc123"
        )
        self.assertEqual(rec["asignatura"], "Marketing Digital")
        self.assertEqual(len(rec["resultados_aprendizaje"]), 3)
        all_skills = _all_skills_flat(rec["skills"])
        self.assertIn("SEO", all_skills, f"SEO not in skills: {all_skills}")

    def test_normalize_skills_no_duplicates(self):
        skills = normalize_skills(self.block1_response["skills"])
        all_skills = _all_skills_flat(skills)
        lower = [_normalize_text(s) for s in all_skills]
        self.assertEqual(len(lower), len(set(lower)),
                         f"Duplicate skills found: {all_skills}")

    def test_preview_runs_without_db(self):
        blocks = split_into_blocks(SAMPLE_TEXT, self.programa)
        records = [
            build_record(blocks[0], self.block1_response,
                         self.programa, self.domain, "sample.txt", "abc123"),
            build_record(blocks[1], self.block2_response,
                         self.programa, self.domain, "sample.txt", "abc123"),
        ]
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_preview(records, [], self.programa, self.domain)
        output = buf.getvalue()
        self.assertIn("Comercio Electrónico", output)
        self.assertIn("Marketing Digital", output)


# ── TestSnapshotCounts ─────────────────────────────────────────────────────────

DB_URL = os.environ.get("RAILWAY_DATABASE_URL") or os.environ.get("DATABASE_URL")

@unittest.skipUnless(DB_URL, "RAILWAY_DATABASE_URL not set — skipping DB regression tests")
class TestSnapshotCounts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        snapshot_path = FIXTURES / "db_snapshot.json"
        cls.snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        from scripts.load_microcurriculos import get_conn
        cls.conn = get_conn()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn") and cls.conn:
            cls.conn.close()

    def test_programa_counts(self):
        failures = []
        for esp_id_str, prog_data in self.snapshot["programs"].items():
            esp_id = int(esp_id_str)
            nombre = prog_data["nombre"]
            min_asignaturas = prog_data["expected_asignaturas_min"]
            min_skills = prog_data["expected_skills_min"]

            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM microcurriculos WHERE specialization_id = %s",
                    (esp_id,),
                )
                asig_count = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT COUNT(*) FROM microcurriculo_skills ms
                    JOIN microcurriculos m ON ms.microcurriculo_id = m.id
                    WHERE m.specialization_id = %s
                    """,
                    (esp_id,),
                )
                skill_count = cur.fetchone()[0]

            if asig_count < min_asignaturas:
                failures.append(
                    f"esp_id={esp_id} ({nombre}): "
                    f"asignaturas={asig_count} < min={min_asignaturas}"
                )
            if skill_count < min_skills:
                failures.append(
                    f"esp_id={esp_id} ({nombre}): "
                    f"skills={skill_count} < min={min_skills}"
                )

        if failures:
            self.fail("DB regression failures:\n" + "\n".join(failures))


# ── conftest-style pytest fixture (also works as plain pytest) ─────────────────

def pytest_addoption(parser):
    try:
        parser.addoption(
            "--generate-snapshot", action="store_true", default=False,
            help="Regenerate tests/fixtures/db_snapshot.json from live DB"
        )
    except Exception:
        pass


def pytest_configure(config):
    pass


def captura_snapshot(request):
    """Pytest fixture: regenerate db_snapshot.json if --generate-snapshot passed."""
    if not request.config.getoption("--generate-snapshot", default=False):
        return
    if not DB_URL:
        print("WARNING: --generate-snapshot passed but RAILWAY_DATABASE_URL not set")
        return

    from scripts.load_microcurriculos import get_conn
    conn = get_conn()
    snapshot_path = FIXTURES / "db_snapshot.json"
    existing = json.loads(snapshot_path.read_text(encoding="utf-8"))

    for esp_id_str in existing["programs"]:
        esp_id = int(esp_id_str)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM microcurriculos WHERE specialization_id = %s", (esp_id,)
            )
            asig_count = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*) FROM microcurriculo_skills ms
                JOIN microcurriculos m ON ms.microcurriculo_id = m.id
                WHERE m.specialization_id = %s
                """,
                (esp_id,),
            )
            skill_count = cur.fetchone()[0]

        existing["programs"][esp_id_str]["expected_asignaturas_min"] = asig_count
        existing["programs"][esp_id_str]["expected_skills_min"] = skill_count

    import datetime
    existing["_generated"] = datetime.datetime.utcnow().isoformat()
    snapshot_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    conn.close()
    print(f"Snapshot updated: {snapshot_path}")


if __name__ == "__main__":
    unittest.main()
