from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


SECTION_ALIASES = {
    "competencias": ("competencias", "competencia general", "competencias especificas"),
    "resultados_aprendizaje": ("resultados de aprendizaje", "resultados aprendizaje", "learning outcomes"),
    "contenidos": ("contenidos", "contenido tematico", "unidades", "temario"),
    "metodologias": ("metodologia", "metodologias", "estrategias pedagogicas"),
    "bibliografia": ("bibliografia", "referencias", "bibliografía"),
    "herramientas": ("herramientas", "software", "plataformas", "recursos tecnologicos"),
}


@dataclass(frozen=True)
class ParsedMicrocurriculum:
    programa: str = ""
    asignatura: str = ""
    semestre: str = ""
    creditos: str = ""
    competencias: list[str] = field(default_factory=list)
    resultados_aprendizaje: list[str] = field(default_factory=list)
    contenidos: list[str] = field(default_factory=list)
    metodologias: list[str] = field(default_factory=list)
    bibliografia: list[str] = field(default_factory=list)
    herramientas: list[str] = field(default_factory=list)
    raw_sections: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _field_value(text: str, labels: tuple[str, ...]) -> str:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?im)^\s*(?:{label_pattern})\s*[:\-]\s*(.+?)\s*$"
    match = re.search(pattern, text)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _split_items(value: str) -> list[str]:
    candidates = re.split(r"(?:\n|•|\u2022|;|\s-\s|\d+\.\s+)", value)
    items = [re.sub(r"\s+", " ", item).strip(" -:\t") for item in candidates]
    return [item for item in items if len(item) >= 4]


def _find_sections(text: str) -> dict[str, str]:
    headings: list[tuple[str, int, int]] = []
    for canonical, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            for match in re.finditer(rf"(?im)^\s*{re.escape(alias)}\s*:?\s*$", text):
                headings.append((canonical, match.start(), match.end()))
    headings.sort(key=lambda item: item[1])
    sections: dict[str, str] = {}
    for index, (canonical, _start, end) in enumerate(headings):
        next_start = headings[index + 1][1] if index + 1 < len(headings) else len(text)
        body = text[end:next_start].strip()
        if body and canonical not in sections:
            sections[canonical] = body
    return sections


def parse_microcurriculum(text: str) -> ParsedMicrocurriculum:
    sections = _find_sections(text)
    asignatura = _field_value(text, ("asignatura", "curso", "materia", "nombre asignatura"))
    programa = _field_value(text, ("programa", "programa academico", "programa académico"))
    if not programa:
        program_match = re.search(
            r"Microcurr[ií]culos\s+del\s+programa\s+de\s+(.+?)(?:\s+Fundaci[oó]n|\s+UNIR|\n)",
            text,
            re.I,
        )
        if program_match:
            programa = re.sub(r"\s+", " ", program_match.group(1)).strip()
    semestre = _field_value(text, ("semestre", "periodo", "nivel"))
    creditos = _field_value(text, ("creditos", "créditos", "numero de creditos", "número de créditos"))
    if not asignatura and programa:
        asignatura = "Microcurriculos del programa"
    if not asignatura:
        first_title = re.search(r"(?im)^\s*(?!ASIGNATURA\b|APRENDIZAJE\b|SEMESTRE\b)([A-ZÁÉÍÓÚÑ][^\n]{6,90})$", text)
        asignatura = re.sub(r"\s+", " ", first_title.group(1)).strip() if first_title else ""
    return ParsedMicrocurriculum(
        programa=programa,
        asignatura=asignatura,
        semestre=semestre,
        creditos=creditos,
        competencias=_split_items(sections.get("competencias", "")),
        resultados_aprendizaje=_split_items(sections.get("resultados_aprendizaje", "")),
        contenidos=_split_items(sections.get("contenidos", "")),
        metodologias=_split_items(sections.get("metodologias", "")),
        bibliografia=_split_items(sections.get("bibliografia", "")),
        herramientas=_split_items(sections.get("herramientas", "")),
        raw_sections=sections,
    )
