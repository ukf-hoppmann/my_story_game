"""Errors raised by the storygame domain model."""


class DomainError(Exception):
    """Base class for expected domain failures."""


class ValidationError(DomainError):
    """A domain object violates one of its invariants."""


class InvalidReferenceError(ValidationError):
    """A domain object refers to an entity that is not available."""


class RevisionConflictError(DomainError):
    """A change was based on a state revision that is no longer current."""


class ChangeRejectedError(DomainError):
    """A change set was not approved for canonical application."""
