from __future__ import annotations

import re
import unicodedata


def clean_unicode(text: str | None) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.replace("\x00", " ")
    value = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", value)
    return value


def remove_repeated_headers_footers(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in clean_unicode(text).splitlines()]
    lines = [line for line in lines if line]
    counts: dict[str, int] = {}
    for line in lines:
        if len(line) <= 100:
            counts[line.casefold()] = counts.get(line.casefold(), 0) + 1
    repeated = {line for line, count in counts.items() if count >= 3}
    cleaned = [line for line in lines if line.casefold() not in repeated and not re.fullmatch(r"pagina\s+\d+(\s+de\s+\d+)?", line, re.I)]
    return "\n".join(cleaned)


def normalize_whitespace(text: str | None) -> str:
    value = clean_unicode(text)
    value = remove_repeated_headers_footers(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()
