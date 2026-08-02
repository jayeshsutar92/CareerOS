class AgentError(Exception):
    """Base exception for agent framework errors."""


class AgentRegistrationError(AgentError):
    """Raised when agent registration or discovery fails."""


class AgentValidationError(AgentError):
    """Raised when an agent request is invalid."""


class AgentExecutionError(AgentError):
    """Raised when an agent execution fails after retries."""
