from __future__ import annotations

from pathlib import Path

from intelligence import observatory_pipeline


class FakeCursor:
    def __init__(self, table_state: dict[str, bool], counts: dict[str, int] | None = None) -> None:
        self.table_state = table_state
        self.counts = counts or {}
        self.executed: list[tuple[str, tuple | None]] = []
        self._last_result: dict[str, object] = {}

    def execute(self, query: str, params: tuple | None = None) -> None:
        self.executed.append((query, params))
        if "to_regclass" in query:
            table = str(params[0]) if params else ""
            self._last_result = {"exists": self.table_state.get(table, False)}
        elif "COUNT(*)" in query:
            table = query.split("FROM", 1)[1].strip().split()[0]
            self._last_result = {"total": self.counts.get(table, 0)}
        else:
            self._last_result = {}

    def fetchone(self) -> dict[str, object]:
        return self._last_result


def test_validate_observatory_tables_partial() -> None:
    cursor = FakeCursor(
        {
            "observatory_metrics": True,
            "curriculum_gap_observatory": False,
            "recommendation_observatory": False,
            "semantic_role_graph": True,
            "company_observatory": False,
            "emerging_technology_observatory": False,
        },
        {
            "observatory_metrics": 4,
            "semantic_role_graph": 9,
        },
    )

    result = observatory_pipeline._validate_observatory_tables(cursor)

    assert result["status"] == "partial_observatory"
    assert result["completion_percentage"] == 33.33
    assert result["observatory_tables"]["observatory_metrics"] is True
    assert result["observatory_tables"]["curriculum_gap_observatory"] is False
    assert result["table_counts"]["observatory_metrics"] == 4
    assert result["missing_tables"] == [
        "curriculum_gap_observatory",
        "recommendation_observatory",
        "company_observatory",
        "emerging_technology_observatory",
    ]


def test_validate_observatory_tables_ready() -> None:
    cursor = FakeCursor({table: True for table in observatory_pipeline.OBSERVATORY_TABLES}, {table: 1 for table in observatory_pipeline.OBSERVATORY_TABLES})

    result = observatory_pipeline._validate_observatory_tables(cursor)

    assert result["status"] == "observatory_ready"
    assert result["completion_percentage"] == 100.0
    assert all(result["observatory_tables"].values())
    assert not result["missing_tables"]


def test_write_observatory_materialization_report(tmp_path, monkeypatch) -> None:
    report_path = tmp_path / "observatory_materialization_report.md"
    monkeypatch.setattr(observatory_pipeline, "OBSERVATORY_MATERIALIZATION_REPORT", report_path)

    report = observatory_pipeline._write_observatory_materialization_report(
        {
            "status": "observatory_ready",
            "completion_percentage": 100.0,
            "table_counts": {table: 3 for table in observatory_pipeline.OBSERVATORY_TABLES},
            "missing_tables": [],
        },
        "2026-05",
    )

    assert Path(report) == report_path
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Observatory Materialization Report" in content
    assert "- Status: observatory_ready" in content


def test_apply_migrations_reads_expected_files(tmp_path, monkeypatch) -> None:
    migration_dir = tmp_path / "database" / "migrations"
    migration_dir.mkdir(parents=True)
    for migration_name in [
        "015_labor_acquisition_warehouse.sql",
        "016_labor_intelligence_enrichment.sql",
        "017_labor_intelligence_qa_feedback.sql",
        "018_labor_curriculum_intelligence.sql",
        "019_labor_observatory_layer.sql",
    ]:
        (migration_dir / migration_name).write_text(f"-- {migration_name}\n", encoding="utf-8")

    monkeypatch.setattr(observatory_pipeline, "MIGRATIONS", [migration_dir / name for name in [
        "015_labor_acquisition_warehouse.sql",
        "016_labor_intelligence_enrichment.sql",
        "017_labor_intelligence_qa_feedback.sql",
        "018_labor_curriculum_intelligence.sql",
        "019_labor_observatory_layer.sql",
    ]])

    cursor = FakeCursor({}, {})
    observatory_pipeline._apply_migrations(cursor)

    executed_sql = [statement for statement, _ in cursor.executed]
    assert len(executed_sql) == 5
    assert "-- 016_labor_intelligence_enrichment.sql" in executed_sql[1]
    assert "-- 017_labor_intelligence_qa_feedback.sql" in executed_sql[2]
    assert "-- 018_labor_curriculum_intelligence.sql" in executed_sql[3]
