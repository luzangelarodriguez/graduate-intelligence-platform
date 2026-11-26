"""
Unit tests for api/market_studies.py.
No database required.
Run with: pytest tests/unit/test_market_studies.py -v
"""
from __future__ import annotations

import urllib.parse

import pytest

from api.market_studies import ALLOWED_VERIFIED_DOMAINS, PROGRAM_STUDIES

REQUIRED_HALLAZGO_KEYS = {"texto", "fuente", "url", "fecha", "verificada"}


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.removeprefix("www.")


# ── Estructura general ────────────────────────────────────────────────────────

class TestProgramStudiesStructure:
    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_top_level_keys_present(self, program_id: int) -> None:
        entry = PROGRAM_STUDIES[program_id]
        for key in ("resumen", "hallazgos", "habilidades_al_alza", "pierde_peso", "evidencia"):
            assert key in entry, f"program {program_id} missing key '{key}'"

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_hallazgo_keys_complete(self, program_id: int) -> None:
        for i, h in enumerate(PROGRAM_STUDIES[program_id]["hallazgos"]):
            missing = REQUIRED_HALLAZGO_KEYS - set(h)
            assert not missing, (
                f"program {program_id} hallazgo[{i}] missing keys: {missing}"
            )

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_hallazgo_has_nonempty_url_fuente_fecha(self, program_id: int) -> None:
        for i, h in enumerate(PROGRAM_STUDIES[program_id]["hallazgos"]):
            assert h["url"], f"program {program_id} hallazgo[{i}] has empty url"
            assert h["fuente"], f"program {program_id} hallazgo[{i}] has empty fuente"
            assert h["fecha"], f"program {program_id} hallazgo[{i}] has empty fecha"

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_verified_hallazgos_use_allowed_domains(self, program_id: int) -> None:
        for i, h in enumerate(PROGRAM_STUDIES[program_id]["hallazgos"]):
            if not h["verificada"]:
                continue
            domain = _domain(h["url"])
            assert any(domain.endswith(allowed) for allowed in ALLOWED_VERIFIED_DOMAINS), (
                f"program {program_id} hallazgo[{i}] verificada=True but domain "
                f"'{domain}' not in ALLOWED_VERIFIED_DOMAINS"
            )

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_evidencia_value_is_valid(self, program_id: int) -> None:
        valid = {"industria", "academica", "mixta"}
        value = PROGRAM_STUDIES[program_id]["evidencia"]
        assert value in valid, (
            f"program {program_id} evidencia='{value}' not in {valid}"
        )

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_pierde_peso_has_lectura_propia(self, program_id: int) -> None:
        pp = PROGRAM_STUDIES[program_id]["pierde_peso"]
        assert "texto" in pp, f"program {program_id} pierde_peso missing 'texto'"
        assert "lectura_propia" in pp, f"program {program_id} pierde_peso missing 'lectura_propia'"

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_habilidades_al_alza_nonempty(self, program_id: int) -> None:
        lst = PROGRAM_STUDIES[program_id]["habilidades_al_alza"]
        assert isinstance(lst, list) and len(lst) > 0, (
            f"program {program_id} habilidades_al_alza is empty"
        )


# ── Dominio y contenido ──────────────────────────────────────────────────────

class TestContentRules:
    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_no_iadb_in_urls(self, program_id: int) -> None:
        for i, h in enumerate(PROGRAM_STUDIES[program_id]["hallazgos"]):
            assert "iadb.org" not in h["url"], (
                f"program {program_id} hallazgo[{i}] url contains 'iadb.org'"
            )

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_no_placeholder_urls(self, program_id: int) -> None:
        """Within a program, the same URL must not appear for different institutions."""
        seen: dict[str, str] = {}  # url → fuente
        for i, h in enumerate(PROGRAM_STUDIES[program_id]["hallazgos"]):
            url = h["url"]
            fuente = h["fuente"]
            if url in seen:
                prev = seen[url]
                # Same URL is acceptable only when both fuentes cite the same institution
                # (defined as sharing the first significant word, case-insensitive).
                prev_first = prev.lower().split()[0]
                curr_first = fuente.lower().split()[0]
                assert prev_first == curr_first, (
                    f"program {program_id} hallazgo[{i}]: URL '{url}' shared by "
                    f"unrelated fuentes:\n  '{prev}'\n  '{fuente}'"
                )
            seen[url] = fuente

    @pytest.mark.parametrize("program_id", list(PROGRAM_STUDIES))
    def test_no_quotes_in_texts(self, program_id: int) -> None:
        quote_chars = ('"', '“', '”')
        for i, h in enumerate(PROGRAM_STUDIES[program_id]["hallazgos"]):
            for ch in quote_chars:
                assert ch not in h["texto"], (
                    f"program {program_id} hallazgo[{i}] texto contains quote char {ch!r}"
                )


# ── Programas esperados ───────────────────────────────────────────────────────

class TestExpectedPrograms:
    def test_all_expected_program_ids_present(self) -> None:
        expected = {13, 146, 9, 109, 11, 20}
        assert expected.issubset(set(PROGRAM_STUDIES)), (
            f"Missing program ids: {expected - set(PROGRAM_STUDIES)}"
        )

    def test_fallback_for_unknown_program(self) -> None:
        result = PROGRAM_STUDIES.get(99999, {"hallazgos": []})
        assert result == {"hallazgos": []}
