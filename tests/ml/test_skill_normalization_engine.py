from __future__ import annotations

from intelligence import skill_normalization_engine as sne


def test_normalize_skill_synonym(monkeypatch) -> None:
    monkeypatch.setattr(sne, "load_skill_catalog", lambda db_name=None: [])
    monkeypatch.setattr(sne, "relation_exists", lambda *args, **kwargs: False)

    result = sne.normalize_skill("PowerBI")

    assert result.canonical_skill == "Power BI"
    assert result.match_method == "generated"
    assert result.confidence_score > 0.6


def test_normalize_skill_fuzzy_match(monkeypatch) -> None:
    monkeypatch.setattr(
        sne,
        "load_skill_catalog",
        lambda db_name=None: [
            {
                "id": 1,
                "canonical_skill": "Data Warehouse",
                "skill_category": "Data Engineering",
                "skill_family": "Data Platform",
            }
        ],
    )
    monkeypatch.setattr(sne, "relation_exists", lambda *args, **kwargs: False)

    result = sne.normalize_skill("data warehousing")

    assert result.canonical_skill == "Data Warehouse"
    assert result.match_method in {"fuzzy", "generated"}


def test_normalize_skill_batch_deduplicates_inputs(monkeypatch) -> None:
    persisted: dict[str, int] = {"count": 0}

    monkeypatch.setattr(
        sne,
        "normalize_skill",
        lambda raw_skill, db_name=None, source_payload=None: sne.SkillNormalizationResult(
            raw_skill=raw_skill,
            raw_skill_normalized=raw_skill.casefold().strip(),
            canonical_skill=raw_skill.strip(),
            canonical_skill_id=None,
            skill_category="Unknown",
            skill_family="Unknown",
            match_method="generated",
            confidence_score=0.75,
            source_payload=source_payload or {},
        ),
    )
    monkeypatch.setattr(sne, "persist_skill_normalization_mappings", lambda records, db_name=None: persisted.__setitem__("count", len(records)) or len(records))

    results = sne.normalize_skill_batch(["AWS", "aws", "Databricks"], persist=True)

    assert len(results) == 2
    assert persisted["count"] == 2
