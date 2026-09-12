import logging
import re
from typing import Any
from collections import defaultdict
from app.lead_discovery.models import CompanyCandidateSet, CanonicalCompanyEntity, DiscoveryEvidence

logger = logging.getLogger(__name__)

# Common corporate suffixes to strip during normalization
LEGAL_SUFFIXES = [
    r'\binc\b\.?', r'\bincorporated\b', r'\bcorp\b\.?', r'\bcorporation\b',
    r'\bllc\b\.?', r'\bplc\b\.?', r'\bltd\b\.?', r'\blimited\b',
    r'\bpvt\b\.?', r'\bprivate\b', r'\bco\b\.?', r'\bcompany\b',
    r'\bgmbh\b\.?', r'\bsa\b\.?', r'\bas\b\.?', r'\bab\b\.?'
]
SUFFIX_PATTERN = re.compile(r'(' + '|'.join(LEGAL_SUFFIXES) + r')', flags=re.IGNORECASE)

class EntityResolver:
    def __init__(self, min_confidence: int = 40):
        self.min_confidence = min_confidence

    def normalize_name(self, name: str) -> str:
        """Strip legal suffixes and normalize spacing/casing."""
        # Remove common punctuation and weird characters that job boards add
        clean = re.sub(r'[^\w\s&@-]', ' ', name)
        
        # Strip suffixes
        clean = SUFFIX_PATTERN.sub('', clean)
        
        # Normalize whitespace and casing
        clean = ' '.join(clean.split()).lower().strip()
        
        # Drop trailing '&', '-', '@'
        clean = re.sub(r'[\-&@\s]+$', '', clean).strip()
        return clean

    def generate_canonical_id(self, normalized_name: str, location: str) -> str:
        """Generate a deterministic identity key."""
        loc = ' '.join(re.sub(r'[^\w\s]', '', location).split()).lower()
        return f"{normalized_name}::{loc}"

    def resolve_entities(self, candidate_set: CompanyCandidateSet, location: str) -> list[CanonicalCompanyEntity]:
        """
        Group raw candidates into canonical entities, score them, and filter out low confidence.
        Returns a list of ranked CanonicalCompanyEntity objects.
        """
        canonical_map: dict[str, CanonicalCompanyEntity] = {}
        rejected_count = 0
        
        # Flatten all evidence from the CandidateSet for authoritative clustering
        all_evidence = []
        for candidate in candidate_set.candidates:
            all_evidence.extend(candidate.evidence)
            
        for evidence in all_evidence:
            norm = self.normalize_name(evidence.original_name)
            if not norm or len(norm) < 2:
                logger.debug("Dropped evidence due to invalid normalized name", extra={"raw_name": evidence.original_name})
                rejected_count += 1
                continue
                
            canonical_id = self.generate_canonical_id(norm, location)
            
            if canonical_id not in canonical_map:
                canonical_map[canonical_id] = CanonicalCompanyEntity(
                    canonical_id=canonical_id,
                    normalized_name=norm,
                    evidence=[]
                )
            
            # Prevent duplicate identical evidence within the same cluster
            cluster = canonical_map[canonical_id]
            if not any(e.source_url == evidence.source_url and e.provider == evidence.provider for e in cluster.evidence):
                cluster.evidence.append(evidence)
            
        resolved_entities = []
        
        for cid, entity in canonical_map.items():
            # Additional score for appearing across multiple providers
            distinct_providers = set(e.provider for e in entity.evidence)
            aggregate_score = entity.aggregate_score
            
            # Ranking signal: Provider Agreement
            if len(distinct_providers) > 1:
                aggregate_score += (len(distinct_providers) * 10)
                
            # Filter low confidence entities if needed (though we rely on sorting later)
            if aggregate_score < self.min_confidence:
                logger.debug("Dropped entity due to low confidence", extra={"canonical_id": cid, "score": aggregate_score})
                rejected_count += 1
                continue
                
            resolved_entities.append(entity)
            
            logger.info("Entity clustered and resolved", extra={
                "action": "entity_resolved",
                "canonical_id": cid,
                "normalized_name": entity.normalized_name,
                "original_names": list(set(e.original_name for e in entity.evidence)),
                "providers": list(distinct_providers),
                "aggregate_score": aggregate_score,
                "selected_name": entity.best_original_name
            })
            
        # Rank the entities
        ranked_entities = sorted(resolved_entities, key=lambda e: (len(set(ev.provider for ev in e.evidence)), e.aggregate_score), reverse=True)
        
        logger.info("Entity Resolution finished", extra={
            "raw_evidence_count": len(all_evidence),
            "rejected_evidence": rejected_count,
            "canonical_entities": len(ranked_entities)
        })
        
        return ranked_entities

