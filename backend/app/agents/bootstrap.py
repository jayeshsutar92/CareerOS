from app.contact_discovery.agent import register_contact_discovery_agent

_AGENTS_REGISTERED = False


def register_agents() -> None:
    global _AGENTS_REGISTERED
    if _AGENTS_REGISTERED:
        return

    register_contact_discovery_agent()
    _AGENTS_REGISTERED = True
