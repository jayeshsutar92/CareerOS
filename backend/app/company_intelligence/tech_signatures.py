from __future__ import annotations

import re
from typing import NamedTuple


class TechSignature(NamedTuple):
    name: str
    category: str
    patterns: list[re.Pattern[str]]


TECH_SIGNATURES: list[TechSignature] = [
    # Frontend Frameworks & Libraries
    TechSignature("Next.js", "frontend", [re.compile(r"_next/static", re.I), re.compile(r"__NEXT_DATA__", re.I)]),
    TechSignature("React", "frontend", [re.compile(r"react(?:\.production|\.development)?\.js", re.I), re.compile(r"data-reactroot", re.I)]),
    TechSignature("Vue.js", "frontend", [re.compile(r"vue(?:\.runtime|\.global)?\.js", re.I), re.compile(r"data-v-[a-f0-9]", re.I)]),
    TechSignature("Angular", "frontend", [re.compile(r"ng-version", re.I), re.compile(r"angular(?:\.min)?\.js", re.I)]),
    TechSignature("Tailwind CSS", "frontend", [re.compile(r"tailwindcss", re.I), re.compile(r"class=[\"'][^\"']*\b(?:flex|grid|hidden|bg-\w+-\d+)\b", re.I)]),
    TechSignature("Bootstrap", "frontend", [re.compile(r"bootstrap(?:\.min)?\.(?:css|js)", re.I)]),

    # Backend Frameworks & Runtimes
    TechSignature("FastAPI", "backend", [re.compile(r"fastapi", re.I), re.compile(r"/docs#/default", re.I)]),
    TechSignature("Django", "backend", [re.compile(r"csrfmiddlewaretoken", re.I), re.compile(r"django", re.I)]),
    TechSignature("Node.js", "backend", [re.compile(r"express", re.I), re.compile(r"node_modules", re.I)]),
    TechSignature("Laravel", "backend", [re.compile(r"laravel", re.I), re.compile(r"XSRF-TOKEN", re.I)]),

    # Cloud, Hosting & Infra
    TechSignature("Vercel", "infrastructure", [re.compile(r"vercel", re.I), re.compile(r"x-vercel-id", re.I)]),
    TechSignature("AWS", "infrastructure", [re.compile(r"amazonaws\.com", re.I), re.compile(r"aws-sdk", re.I)]),
    TechSignature("Cloudflare", "infrastructure", [re.compile(r"cloudflare", re.I), re.compile(r"__cfduid", re.I)]),
    TechSignature("Google Cloud", "infrastructure", [re.compile(r"storage\.googleapis\.com", re.I)]),

    # Analytics, Payments & Auth
    TechSignature("Google Analytics", "analytics", [re.compile(r"google-analytics\.com", re.I), re.compile(r"googletagmanager\.com", re.I), re.compile(r"gtag\(", re.I)]),
    TechSignature("PostHog", "analytics", [re.compile(r"posthog", re.I)]),
    TechSignature("Stripe", "payments", [re.compile(r"js\.stripe\.com", re.I), re.compile(r"stripe", re.I)]),
    TechSignature("Supabase", "database", [re.compile(r"supabase", re.I)]),
    TechSignature("Firebase", "database", [re.compile(r"firebase", re.I)]),
    TechSignature("Intercom", "customer_support", [re.compile(r"intercom\.io", re.I)]),
]


class TechStackDetector:
    def __init__(self, signatures: list[TechSignature] | None = None) -> None:
        self.signatures = signatures or TECH_SIGNATURES

    def detect(self, html: str, headers: dict[str, str] | None = None) -> list[str]:
        detected: set[str] = set()
        text_content = html
        if headers:
            text_content += " " + " ".join(f"{k}: {v}" for k, v in headers.items())

        for sig in self.signatures:
            for pattern in sig.patterns:
                if pattern.search(text_content):
                    detected.add(sig.name)
                    break

        return sorted(detected)
