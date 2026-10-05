"""In-memory stand-in for the prompt-version ports, shared by several tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from story_game.application.prompt_management import (
    NewPromptVersion,
    PromptEntryKind,
    PromptStoreError,
    PromptVersion,
)


class InMemoryPromptStore:
    """Reader and writer in one: append-only rows, one active row per key."""

    def __init__(self) -> None:
        self.rows: list[PromptVersion] = []
        self.fail_with: PromptStoreError | None = None

    def list_active(self, package_id: str, package_version: str) -> tuple[PromptVersion, ...]:
        self._maybe_fail()
        return tuple(
            row
            for row in self.rows
            if row.is_active
            and row.package_id == package_id
            and row.package_version == package_version
        )

    def list_history(
        self, package_id: str, package_version: str, kind: PromptEntryKind, key: str
    ) -> tuple[PromptVersion, ...]:
        self._maybe_fail()
        matching = [
            row
            for row in self.rows
            if row.package_id == package_id
            and row.package_version == package_version
            and row.entry.kind == kind
            and row.entry.key == key
        ]
        return tuple(sorted(matching, key=lambda row: row.created_at, reverse=True))

    def append_versions(self, versions: Sequence[NewPromptVersion]) -> tuple[PromptVersion, ...]:
        self._maybe_fail()
        created: list[PromptVersion] = []
        for new in versions:
            self.rows = [
                replace(row, is_active=False)
                if row.is_active
                and (row.package_id, row.package_version, row.entry.kind, row.entry.key)
                == (new.package_id, new.package_version, new.entry.kind, new.entry.key)
                else row
                for row in self.rows
            ]
            row = PromptVersion(
                version_id=new.version_id,
                package_id=new.package_id,
                package_version=new.package_version,
                entry=new.entry,
                source=new.source,
                created_at=new.created_at,
                created_by=new.created_by,
                is_active=True,
            )
            self.rows.append(row)
            created.append(row)
        return tuple(created)

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with
