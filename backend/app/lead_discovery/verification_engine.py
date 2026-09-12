import logging
from typing import Any

from app.lead_discovery.models import (
    CanonicalCompanyEntity,
    SocialResolutionEvidence,
    CareersSurfaceSet,
    ContactDiscoveryEvidence,
    VerificationResult,
    VerificationSummary,
    VerificationEvidence
)

logger = logging.getLogger(__name__)

class VerificationEngine:
    def __init__(self):
        pass

    def verify(
        self,
        entity: CanonicalCompanyEntity,
        evidence_coll_dict: dict[str, Any],
        social_evidence: SocialResolutionEvidence,
        careers_surfaces: CareersSurfaceSet,
        contact_evidence: ContactDiscoveryEvidence
    ) -> VerificationEvidence:
        logger.info("Starting verification engine", extra={"company_name": entity.normalized_name, "canonical_id": entity.canonical_id})
        
        summary = VerificationSummary(canonical_id=entity.canonical_id)
        
        # 1. Verify Website & Company Identity
        website_score = entity.website_evidence.confidence if entity.website_evidence else 0
        website_status = "Verified" if website_score >= 80 else ("Likely Verified" if website_score >= 50 else "Needs Review")
        
        summary.results.append(VerificationResult(
            entity_id=entity.canonical_id,
            entity_type="CompanyWebsite",
            status=website_status,
            confidence_score=website_score,
            evidence_summary=["Website resolution confidence: " + str(website_score)],
        ))

        # 2. Verify Social Profiles
        social_score = 100 if social_evidence.resolved_profiles else 0
        social_status = "Verified" if social_score >= 80 else "Unverified"
        summary.results.append(VerificationResult(
            entity_id=entity.canonical_id,
            entity_type="SocialProfiles",
            status=social_status,
            confidence_score=social_score,
            evidence_summary=[f"Resolved {len(social_evidence.resolved_profiles)} profiles"],
        ))

        # 3. Verify Careers Surfaces
        valid_surfaces = [c for c in careers_surfaces.candidates if not c.is_rejected]
        careers_score = 100 if any(c.surface_type == "ats_portal" for c in valid_surfaces) else (80 if valid_surfaces else 0)
        careers_status = "Verified" if careers_score >= 80 else ("Likely Verified" if careers_score >= 50 else "Unverified")
        summary.results.append(VerificationResult(
            entity_id=entity.canonical_id,
            entity_type="CareersSurfaces",
            status=careers_status,
            confidence_score=careers_score,
            evidence_summary=[f"Found {len(valid_surfaces)} valid careers surfaces"],
        ))

        # 4. Verify Contacts
        valid_people = [p for p in contact_evidence.candidate_set.people if not p.is_rejected]
        valid_channels = [c for c in contact_evidence.candidate_set.channels if not c.is_rejected]
        
        contacts_score = 0
        if valid_people:
            contacts_score += 70
        if valid_channels:
            contacts_score += 30
            
        contacts_status = "Verified" if contacts_score >= 80 else ("Likely Verified" if contacts_score >= 50 else "Unverified")
        summary.results.append(VerificationResult(
            entity_id=entity.canonical_id,
            entity_type="Contacts",
            status=contacts_status,
            confidence_score=contacts_score,
            evidence_summary=[f"Found {len(valid_people)} people and {len(valid_channels)} channels"],
        ))

        # Overall Aggregation
        scores = [r.confidence_score for r in summary.results if r.entity_type != "SocialProfiles"] # Social is optional
        summary.overall_confidence = sum(scores) // len(scores) if scores else 0
        summary.overall_status = "Verified" if summary.overall_confidence >= 80 else ("Likely Verified" if summary.overall_confidence >= 50 else "Needs Review")

        logger.info("Verification engine finished", extra={
            "company_name": entity.normalized_name,
            "overall_status": summary.overall_status,
            "overall_confidence": summary.overall_confidence
        })

        return VerificationEvidence(
            canonical_id=entity.canonical_id,
            summary=summary
        )
