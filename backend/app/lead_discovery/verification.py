import logging
from typing import Any
from app.lead_discovery.search import CompanyLead

logger = logging.getLogger(__name__)

class VerificationStage:
    """
    Evaluates accumulated evidence from Phase 1 (Entity), Phase 2 (Website/Socials), 
    and Phase 3 (Contacts) to determine confidence scores and verification status 
    without performing any additional network requests.
    """
    
    COMPANY_VERIFIED_THRESHOLD = 50
    CONTACT_VERIFIED_THRESHOLD = 50

    def verify(self, company_lead: CompanyLead, contacts: list[dict]) -> dict:
        """
        Takes a CompanyLead and its discovered contacts (as dictionaries), 
        evaluates their evidence, and returns an enriched result with verification data.
        """
        # 1. Verify Company
        company_result = self._verify_company(company_lead)
        
        # 2. Verify Contacts
        verified_contacts = []
        unverified_contacts = []
        
        for contact_dict in contacts:
            verified_contact = self._verify_contact(contact_dict)
            if verified_contact["is_verified"]:
                verified_contacts.append(verified_contact)
            else:
                unverified_contacts.append(verified_contact)
                
        # 3. Sort contacts by confidence
        verified_contacts.sort(key=lambda x: x["confidence_score"], reverse=True)
        unverified_contacts.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        # 4. Final Aggregated Result
        # Preserve API contract: flat contacts list but with verification fields inside
        all_contacts = verified_contacts + unverified_contacts
        
        company_result["contacts"] = all_contacts
        company_result["verified_contacts"] = verified_contacts
        company_result["unverified_contacts"] = unverified_contacts
        company_result["contacts_count"] = len(all_contacts)
        company_result["verified_contacts_count"] = len(verified_contacts)
        
        # Company score is the sum of verified contacts confidence
        company_result["company_score"] = sum(c["confidence_score"] for c in verified_contacts)
        
        logger.info(
            "Verification stage completed for company",
            extra={
                "action": "verification_completed",
                "company_name": company_result["name"],
                "is_verified": company_result["is_verified"],
                "total_contacts": company_result["contacts_count"],
                "verified_contacts": company_result["verified_contacts_count"]
            }
        )
        
        return company_result

    def _verify_company(self, lead: CompanyLead) -> dict:
        identity_confidence = lead.source_score
        website_confidence = lead.website_confidence
        
        # Calculate social confidence based on resolution evidence
        social_confidence = 0
        if lead.socials:
            social_confidence += 30
            
        total_confidence = (identity_confidence + website_confidence + social_confidence) / 3
        is_verified = total_confidence >= self.COMPANY_VERIFIED_THRESHOLD
        
        summary = {
            "identity_confidence": identity_confidence,
            "website_confidence": website_confidence,
            "social_confidence": social_confidence,
            "total_confidence": int(total_confidence),
            "rationale": f"Identity ({identity_confidence}), Website ({website_confidence}), Socials ({social_confidence})",
            "resolution_evidence": lead.resolution_evidence
        }
        
        return {
            "name": lead.name,
            "url": lead.url,
            "is_verified": is_verified,
            "confidence_score": int(total_confidence),
            "verification_summary": summary,
            "socials": lead.socials
        }

    def _verify_contact(self, contact: dict) -> dict:
        base_score = contact.get("confidence_score", 0)
        evidence = contact.get("discovery_evidence", {})
        methods = contact.get("contact_methods", [])
        
        email_confidence = 0
        email_address = None
        has_email = False
        
        for method in methods:
            if method.get("type") == "email":
                has_email = True
                email_address = method.get("value", "")
                if email_address and email_address.lower().startswith(("hr@", "careers@", "jobs@", "talent@")):
                    email_confidence += 30
                elif email_address:
                    email_confidence += 50
                    
        total_confidence = base_score + email_confidence
        total_confidence = min(total_confidence, 100)
        
        is_verified = total_confidence >= self.CONTACT_VERIFIED_THRESHOLD
        
        rationale_parts = [f"Base extraction score: {base_score}"]
        if has_email:
            rationale_parts.append(f"Email bonus: +{email_confidence}")
        if evidence:
            provider = evidence.get("provider", "unknown")
            method = evidence.get("extraction_method", "unknown")
            rationale_parts.append(f"Provider: {provider} ({method})")
            
        summary = {
            "base_score": base_score,
            "email_confidence": email_confidence,
            "total_confidence": total_confidence,
            "rationale": " | ".join(rationale_parts),
            "discovery_evidence": evidence
        }
        
        # Create a new dict preserving the original fields
        verified_contact = contact.copy()
        verified_contact.update({
            "confidence_score": total_confidence, # Update with any bonuses
            "is_verified": is_verified,
            "verification_summary": summary,
            "has_email": has_email,
            "email": email_address
        })
        
        return verified_contact
