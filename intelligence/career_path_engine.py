from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from intelligence.common import clamp
from intelligence.semantic_role_intelligence import RoleSignal


CAREER_ORDER = [
    "Data Analyst",
    "BI Analyst",
    "Reporting Analyst",
    "Analytics Engineer",
    "Data Engineer",
    "Cloud Analytics Engineer",
    "Data Architect",
]

CRIMINOLOGY_CAREER_ORDER = [
    "Criminal Research Assistant",
    "Forensic Analyst",
    "Victim Assistance Specialist",
    "Criminal Intelligence Analyst",
    "Cybercrime Investigator",
    "Public Security Advisor",
    "Criminal Policy Analyst",
]


@dataclass(frozen=True)
class CareerTransition:
    source_role: str
    target_role: str
    role_progression_probability: float
    transition_skill_gaps: list[str]
    recommended_next_skills: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_career_paths(role_signals: list[RoleSignal], market_skills: list[str]) -> list[CareerTransition]:
    present_titles = {signal.role_title.casefold(): signal.role_title for signal in role_signals}
    criminology_markers = {"criminal investigation", "forensic analysis", "victimology", "criminal intelligence", "crime prevention", "public security", "cybercrime", "chain of custody", "organized crime", "financial crime"}
    selected_order = CRIMINOLOGY_CAREER_ORDER if {skill.casefold() for skill in market_skills} & criminology_markers or any("criminal" in signal.role_family.casefold() or "forensic" in signal.role_family.casefold() for signal in role_signals) else CAREER_ORDER
    transitions: list[CareerTransition] = []
    for left, right in zip(selected_order, selected_order[1:]):
        source = present_titles.get(left.casefold(), left)
        target = present_titles.get(right.casefold(), right)
        if selected_order is CRIMINOLOGY_CAREER_ORDER:
            gaps = [skill for skill in ("criminal investigation", "forensic analysis", "victimology", "criminal intelligence", "crime prevention", "public security", "cybercrime", "chain of custody", "risk analysis", "compliance") if skill in market_skills]
        else:
            gaps = [skill for skill in ("SQL", "Power BI", "Python", "ETL", "Azure", "Databricks", "data governance") if skill in market_skills]
        probability = 0.45
        if source in present_titles.values() or target in present_titles.values():
            probability += 0.20
        probability += min(len(gaps) / 20, 0.25)
        transitions.append(
            CareerTransition(
                source_role=source,
                target_role=target,
                role_progression_probability=round(clamp(probability), 4),
                transition_skill_gaps=gaps[:5],
                recommended_next_skills=gaps[:5],
            )
        )
    return transitions
