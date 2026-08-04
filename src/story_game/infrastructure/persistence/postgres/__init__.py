"""PostgreSQL adapter for revisioned canonical game-state snapshots."""

from .connection import PostgresConnectionFactory
from .migrations import PostgresSchemaMigrator
from .store import PostgresGameStateStore

__all__ = [
    "PostgresConnectionFactory",
    "PostgresGameStateStore",
    "PostgresSchemaMigrator",
]
