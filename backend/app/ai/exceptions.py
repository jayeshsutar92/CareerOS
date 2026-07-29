class AIError(Exception):
    """Base exception for AI infrastructure errors."""


class AIConfigurationError(AIError):
    """Raised when AI configuration is missing or invalid."""


class AIProviderError(AIError):
    """Raised when an AI provider request fails."""


class AIPromptError(AIError):
    """Raised when prompt rendering fails."""
