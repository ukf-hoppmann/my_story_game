"""Errors raised at the persistence boundary."""


class PersistenceError(Exception):
    """Base class for persistence failures."""


class PersistenceNotFoundError(PersistenceError):
    """The requested run or revision does not exist."""


class PersistenceConflictError(PersistenceError):
    """A persistence operation lost an optimistic concurrency race."""


class PersistenceConsistencyError(PersistenceError):
    """Stored rows cannot be reconstructed into a valid domain state."""
