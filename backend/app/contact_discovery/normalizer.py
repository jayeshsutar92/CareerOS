from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from app.schemas.contact import ContactCandidate, ContactMethod, ContactRoleCategory

ROLE_PATTERNS: tuple[tuple[ContactRoleCategory, re.Pattern[str]], ...] = (
    (
        "engineering_manager",
        re.compile(r"\b(engineering manager|engineering lead|head of engineering)\b", re.I),
    ),
    (
        "hiring_manager",
        re.compile(r"\b(hiring manager|talent acquisition manager|people manager)\b", re.I),
    ),
    (
        "recruiter",
        re.compile(r"\b(recruiter|technical recruiter|talent acquisition|sourcer)\b", re.I),
    ),
    ("hr", re.compile(r"\b(hr|human resources|people operations|people partner)\b", re.I)),
)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def classify_role(role: str) -> ContactRoleCategory:
    normalized_role = normalize_whitespace(role)
    for category, pattern in ROLE_PATTERNS:
        if pattern.search(normalized_role):
            return category
    return "other"


def normalize_contact_methods(methods: Iterable[ContactMethod]) -> list[dict[str, str]]:
    deduped: dict[tuple[str, str], dict[str, str]] = {}
    for method in methods:
        value = normalize_whitespace(method.value)
        if method.type == "email":
            value = value.lower()
        key = (method.type, value.lower())
        deduped[key] = {"type": method.type, "value": value}
    return list(deduped.values())


def build_dedupe_key(candidate: ContactCandidate) -> str:
    methods = normalize_contact_methods(candidate.contact_methods)
    primary_method = methods[0]["value"].lower() if methods else str(candidate.source_url).lower()
    raw_key = "|".join(
        [
            normalize_whitespace(candidate.company_name).lower(),
            normalize_whitespace(candidate.name).lower(),
            normalize_whitespace(candidate.role).lower(),
            primary_method,
        ]
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
