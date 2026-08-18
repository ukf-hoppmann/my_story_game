"""PostgreSQL adapter for revisioned canonical game-state snapshots."""

from .connection import PostgresConnectionFactory
from .migrations import PostgresSchemaMigrator
from .store import PostgresGameStore

__all__ = [
    "PostgresConnectionFactory",
    "PostgresGameStore",
    "PostgresSchemaMigrator",
]
