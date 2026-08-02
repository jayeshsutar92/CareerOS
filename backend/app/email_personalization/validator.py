from __future__ import annotations

import re

PLACEHOLDER_REGEXES = [
    re.compile(r"\[(?:Name|Company|Your\s+Name|Your\s+name|GitHub|Email|Role|Title|Product|Specific\s+Detail|Specific\s+Workflow|Name/Role)\]", re.I),
    re.compile(r"\{\{\s*[\w\.\_]+\s*\}\}"),
    re.compile(r"\[[A-Z_]{2,}\]"),
]


class EmailPersonalizationValidator:
    def validate(self, subject: str, body: str) -> tuple[bool, float, list[str]]:
        warnings: list[str] = []
        score: float = 1.0

        # Check 1: Empty or extremely short content
        if not subject or len(subject.strip()) < 3:
            warnings.append("Subject line is too short or empty")
            score -= 0.4
        if not body or len(body.strip()) < 30:
            warnings.append("Email body is too short or empty")
            score -= 0.5

        # Check 2: Unreplaced Placeholders
        text_to_check = f"{subject}\n{body}"
        has_unreplaced = False
        for regex in PLACEHOLDER_REGEXES:
            matches = regex.findall(text_to_check)
            if matches:
                warnings.append(f"Unreplaced placeholders detected: {', '.join(set(matches))}")
                score -= 0.5
                has_unreplaced = True

        # Check 3: Repetition Check (e.g. repeated paragraphs or sentences)
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) != len(set(lines)):
            warnings.append("Duplicate lines or repeated paragraphs detected in email body")
            score -= 0.2

        score = max(0.0, min(1.0, round(score, 2)))
        is_valid = score >= 0.6 and not has_unreplaced and not any("empty" in w for w in warnings)

        return is_valid, score, warnings
