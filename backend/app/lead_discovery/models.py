from dataclasses import dataclass, field
from typing import Any

@dataclass
class DiscoveryEvidence:
    provider: str
    original_name: str
    source_url: str
    confidence: int

@dataclass
class CompanyCandidate:
    normalized_name: str
    evidence: list[DiscoveryEvidence] = field(default_factory=list)

    @property
    def aggregate_confidence(self) -> int:
        return sum(e.confidence for e in self.evidence)
    
    @property
    def best_original_name(self) -> str:
        if not self.evidence:
            return self.normalized_name
        # Select the longest valid name, or the one from the highest confidence provider
        valid_names = [e for e in self.evidence if 2 < len(e.original_name) < 50]
        if not valid_names:
            valid_names = self.evidence
        best = max(valid_names, key=lambda e: (e.confidence, len(e.original_name)))
        return best.original_name

@dataclass
class CompanyCandidateSet:
    candidates: list[CompanyCandidate] = field(default_factory=list)
    
    def add_candidate(self, normalized_name: str, evidence: DiscoveryEvidence) -> None:
        for c in self.candidates:
            if c.normalized_name == normalized_name:
                # Deduplicate by URL and provider to avoid duplicate identical evidence
                if any(e.source_url == evidence.source_url and e.provider == evidence.provider for e in c.evidence):
                    return
                c.evidence.append(evidence)
                return
        self.candidates.append(CompanyCandidate(normalized_name=normalized_name, evidence=[evidence]))
    
    def get_ranked_candidates(self) -> list[CompanyCandidate]:
        return sorted(self.candidates, key=lambda c: c.aggregate_confidence, reverse=True)

@dataclass
class WebsiteCandidate:
    domain: str
    url: str
    score: int
    source: str
    is_rejected: bool = False
    rejection_reason: str = ""
    evidence_signals: list[str] = field(default_factory=list)

@dataclass
class WebsiteCandidateSet:
    candidates: list[WebsiteCandidate] = field(default_factory=list)
    
    def get_ranked_valid_candidates(self) -> list[WebsiteCandidate]:
        return sorted([c for c in self.candidates if not c.is_rejected], key=lambda x: x.score, reverse=True)

@dataclass
class WebsiteResolutionEvidence:
    selected_url: str
    confidence: int
    candidate_set: WebsiteCandidateSet
    ai_arbitration_used: bool = False

@dataclass
class CanonicalCompanyEntity:
    canonical_id: str
    normalized_name: str
    evidence: list[DiscoveryEvidence] = field(default_factory=list)
    website_evidence: WebsiteResolutionEvidence | None = None
    
    @property
    def aggregate_score(self) -> int:
        return sum(e.confidence for e in self.evidence)
        
    @property
    def best_original_name(self) -> str:
        if not self.evidence:
            return self.normalized_name
        valid_names = [e for e in self.evidence if 2 < len(e.original_name) < 50]
        if not valid_names:
            valid_names = self.evidence
        best = max(valid_names, key=lambda e: (e.confidence, len(e.original_name)))
        return best.original_name

@dataclass
class ExtractedEvidence:
    evidence_type: str
    value: str
    source_urls: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    first_seen: float = 0.0

@dataclass
class EvidenceCollection:
    canonical_id: str
    evidence: list[ExtractedEvidence] = field(default_factory=list)
    
    def add_evidence(self, ev_type: str, value: str, source_url: str, method: str) -> None:
        if not value: return
        import time
        for ev in self.evidence:
            if ev.evidence_type == ev_type and ev.value == value:
                if source_url not in ev.source_urls:
                    ev.source_urls.append(source_url)
                if method not in ev.methods:
                    ev.methods.append(method)
                return
        self.evidence.append(ExtractedEvidence(
            evidence_type=ev_type,
            value=value,
            source_urls=[source_url],
            methods=[method],
            first_seen=time.time()
        ))
