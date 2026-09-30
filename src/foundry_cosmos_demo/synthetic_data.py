from __future__ import annotations

from itertools import cycle, product
from typing import Iterable


CONDITION_GROUPS = {
    "cardiometabolic": [
        "blood-pressure follow-up",
        "cholesterol medication adherence",
        "prediabetes lifestyle coaching",
        "heart failure weight monitoring",
    ],
    "respiratory": [
        "asthma symptom step-up guidance",
        "viral upper-respiratory self-care",
        "COPD inhaler technique reinforcement",
        "seasonal allergy relief planning",
    ],
    "musculoskeletal": [
        "low-back pain activity modification",
        "knee osteoarthritis movement coaching",
        "ankle sprain recovery planning",
        "workstation ergonomics reinforcement",
    ],
    "behavioral-health": [
        "sleep hygiene reinforcement",
        "stress de-escalation planning",
        "burnout early warning support",
        "caregiver resilience coaching",
    ],
    "preventive-care": [
        "adult vaccination reminders",
        "cancer screening readiness",
        "hydration and heat-safety coaching",
        "healthy eating pattern reinforcement",
    ],
}

CARE_SETTINGS = [
    "primary-care",
    "virtual-visit",
    "urgent-care-triage",
    "care-management",
]

POPULATIONS = [
    "adult",
    "older-adult",
    "working-parent",
    "college-student",
]

GUIDANCE_INTENTS = [
    "self-management",
    "medication-education",
    "follow-up-planning",
    "escalation-triage",
]

RISK_LEVELS = [
    "routine",
    "watchful",
    "priority",
]

SIGNPOSTS = [
    "seek same-day care for worsening breathing difficulty, chest pain, or confusion",
    "contact a clinician within 24 hours for persistent fever, dehydration, or medication side effects",
    "continue home monitoring and routine follow-up when symptoms remain stable",
]


def _compose_content(
    condition_group: str,
    scenario: str,
    care_setting: str,
    population: str,
    intent: str,
    risk_level: str,
    signpost: str,
    ordinal: int,
) -> str:
    return (
        f"Synthetic care-guidance scenario {ordinal}: Provide {intent} guidance for "
        f"{population} patients in {care_setting} workflows who need support with "
        f"{scenario} within the {condition_group} domain. Include home-care advice, "
        f"clear monitoring next steps, and escalation guidance that says to {signpost}. "
        "This content is fictitious, customer-agnostic, and contains no real patient data."
    )


def build_synthetic_guidance_documents(count: int) -> list[dict]:
    """Create deterministic, synthetic healthcare guidance documents."""

    if count <= 0:
        raise ValueError("count must be positive")

    documents: list[dict] = []
    signposts = cycle(SIGNPOSTS)

    combinations: Iterable[tuple[int, str, str, str, str, str]] = product(
        range(10000),
        CARE_SETTINGS,
        POPULATIONS,
        GUIDANCE_INTENTS,
        RISK_LEVELS,
        CONDITION_GROUPS.keys(),
    )

    for ordinal, (sequence, care_setting, population, intent, risk_level, condition_group) in enumerate(
        combinations, start=1
    ):
        scenarios = CONDITION_GROUPS[condition_group]
        scenario = scenarios[(sequence + ordinal - 1) % len(scenarios)]
        signpost = next(signposts)
        content = _compose_content(
            condition_group=condition_group,
            scenario=scenario,
            care_setting=care_setting,
            population=population,
            intent=intent,
            risk_level=risk_level,
            signpost=signpost,
            ordinal=ordinal,
        )

        documents.append(
            {
                "id": f"{condition_group}-{care_setting}-{population}-{intent}-{risk_level}-{ordinal:05d}",
                "conditionGroup": condition_group,
                "careSetting": care_setting,
                "population": population,
                "intent": intent,
                "riskLevel": risk_level,
                "title": f"{scenario.title()} guidance for {population.replace('-', ' ')}",
                "summary": (
                    f"Synthetic {intent} guidance for {scenario} in {care_setting}."
                ),
                "content": content,
                "sourceType": "synthetic",
                "domain": "healthcare-care-guidance",
                "mcpSearchable": True,
                "tags": [
                    condition_group,
                    care_setting,
                    population,
                    intent,
                    risk_level,
                ],
            }
        )

        if len(documents) == count:
            return documents

    return documents


def build_embedding_inputs(documents: list[dict]) -> list[str]:
    return [
        " | ".join(
            [
                document["title"],
                document["summary"],
                document["content"],
                "tags: " + ", ".join(document["tags"]),
            ]
        )
        for document in documents
    ]
