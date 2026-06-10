class DomainError(ValueError):
    """Base exception for domain rule violations."""


class EntityNotFoundError(DomainError):
    """Raised when a requested domain entity does not exist."""
