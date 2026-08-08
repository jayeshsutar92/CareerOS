from app.company_intelligence.agent import register_company_intelligence_agent
from app.contact_discovery.agent import register_contact_discovery_agent
from app.email_personalization.agent import register_email_personalization_agent
from app.lead_discovery.agent import register_lead_discovery_agent

_AGENTS_REGISTERED = False


def register_agents() -> None:
    global _AGENTS_REGISTERED
    if _AGENTS_REGISTERED:
        return

    register_contact_discovery_agent()
    register_company_intelligence_agent()
    register_email_personalization_agent()
    from app.email_delivery.agent import register_email_delivery_agent
    register_email_delivery_agent()
    register_lead_discovery_agent()
    _AGENTS_REGISTERED = True


