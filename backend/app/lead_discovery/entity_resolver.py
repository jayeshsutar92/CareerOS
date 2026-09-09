import logging
import re
from typing import Any
from collections import defaultdict
from app.lead_discovery.search import CompanyLead

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

    def resolve_entities(self, leads: list[CompanyLead], location: str) -> list[CompanyLead]:
        """
        Group raw leads into canonical entities, score them, and filter out low confidence.
        Returns a list of best-representative CompanyLeads.
        """
        canonical_map = defaultdict(list)
        
        for lead in leads:
            norm = self.normalize_name(lead.name)
            if not norm or len(norm) < 2:
                logger.debug("Dropped lead due to invalid normalized name", extra={"raw_name": lead.name})
                continue
                
            canonical_id = self.generate_canonical_id(norm, location)
            canonical_map[canonical_id].append(lead)
            
        resolved_leads = []
        
        for cid, group in canonical_map.items():
            # Calculate aggregate score based on distinct sources
            sources = {}
            for lead in group:
                if lead.source_name not in sources or lead.source_score > sources[lead.source_name]:
                    sources[lead.source_name] = lead.source_score
                    
            aggregate_score = sum(sources.values())
            
            # Additional score for appearing across multiple providers
            if len(sources) > 1:
                aggregate_score += (len(sources) * 10)
                
            norm_name = cid.split("::")[0]
            
            # Select the best representative lead for this entity
            # Prefer leads with longer original names (they usually have better context),
            # but cap it to avoid overly long garbage names.
            valid_names = [l for l in group if 2 < len(l.name) < 50]
            if not valid_names:
                valid_names = group
            best_lead = max(valid_names, key=lambda l: (sources.get(l.source_name, 0), len(l.name)))
            
            # Clone to avoid mutating original
            canonical_lead = CompanyLead(
                name=best_lead.name,
                url=best_lead.url,
                source_score=aggregate_score,
                source_name=" | ".join(sources.keys()),
                is_official_resolved=False
            )
            
            logger.info("Entity resolved", extra={
                "action": "entity_resolved",
                "canonical_id": cid,
                "normalized_name": norm_name,
                "original_names": list(set(l.name for l in group)),
                "sources": list(sources.keys()),
                "aggregate_score": aggregate_score,
                "selected_name": canonical_lead.name
            })
            
            if aggregate_score >= self.min_confidence:
                resolved_leads.append(canonical_lead)
            else:
                logger.warning("Entity rejected - unverified low confidence", extra={
                    "action": "entity_rejected",
                    "canonical_id": cid,
                    "score": aggregate_score,
                    "threshold": self.min_confidence
                })
                
        # Sort by aggregate score descending
        resolved_leads.sort(key=lambda x: x.source_score, reverse=True)
        return resolved_leads

