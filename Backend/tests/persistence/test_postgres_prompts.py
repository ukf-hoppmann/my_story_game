from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

pytest.importorskip("psycopg")

from story_game.application.llm import PromptPackageNotFoundError  # noqa: E402
from story_game.application.prompt_management import (  # noqa: E402
    NewPromptVersion,
    PromptEntry,
    PromptEntryKind,
    PromptVersionSource,
    flatten_package,
)
from story_game.domain import StableId  # noqa: E402
from story_game.infrastructure.llm import FilePromptPackageCatalog  # noqa: E402
from tests.persistence.test_postgres_persistence import postgres_store  # noqa: E402,F401
from tests.application.test_prompt_management import PROMPT_ROOT  # noqa: E402

CREATED = datetime(2026, 10, 5, 12, tzinfo=UTC)


@pytest.fixture
def prompts(postgres_store):  # noqa: F811
    from story_game.infrastructure.persistence.postgres import (
        DbPromptPackageCatalog,
        PostgresPromptStore,
    )

    _, connections = postgres_store
    package_id = f"test.{uuid4().hex[:12]}"
    store = PostgresPromptStore(connections)
    try:
        yield store, DbPromptPackageCatalog(store), package_id
    finally:
        with connections.connect() as connection:
            connection.execute("DELETE FROM system_prompts WHERE package_id = %s", (package_id,))
            connection.commit()


def new(package_id, entry, *, source=PromptVersionSource.TOML_SEED, minutes=0, by=None):
    return NewPromptVersion(
        StableId.new(), package_id, "1", entry, source, CREATED + timedelta(minutes=minutes), by
    )


def test_a_package_seeded_into_postgres_loads_back_identically(prompts) -> None:
    store, catalog, package_id = prompts
    original = FilePromptPackageCatalog(PROMPT_ROOT).load("story.base", "1")
    store.append_versions([new(package_id, entry) for entry in flatten_package(original)])

    loaded = catalog.load(package_id, "1")

    assert loaded.tasks == original.tasks
    assert loaded.categories == original.categories
    assert loaded.directives == original.directives


def test_loading_an_unknown_package_raises_not_found(prompts) -> None:
    _, catalog, package_id = prompts

    with pytest.raises(PromptPackageNotFoundError):
        catalog.load(package_id, "1")


def test_appending_a_version_keeps_the_history_and_one_active_row(prompts) -> None:
    store, catalog, package_id = prompts
    task = PromptEntry(PromptEntryKind.TASK, "story_generation", "Original", 0)
    store.append_versions([new(package_id, task)])

    store.append_versions(
        [
            new(
                package_id,
                PromptEntry(PromptEntryKind.TASK, "story_generation", "Geändert", 0),
                source=PromptVersionSource.UI,
                minutes=1,
                by="admin-1",
            )
        ]
    )

    history = store.list_history(package_id, "1", PromptEntryKind.TASK, "story_generation")
    assert [(v.entry.text, v.source, v.created_by, v.is_active) for v in history] == [
        ("Geändert", PromptVersionSource.UI, "admin-1", True),
        ("Original", PromptVersionSource.TOML_SEED, None, False),
    ]
    active = store.list_active(package_id, "1")
    assert [v.entry.text for v in active] == ["Geändert"]
    assert history[0].created_at == CREATED + timedelta(minutes=1)


def test_a_failing_batch_is_rolled_back_completely(prompts) -> None:
    from story_game.application.prompt_management import PromptStoreError

    store, _, package_id = prompts
    good = PromptEntry(PromptEntryKind.TASK, "a", "Text", 0)
    store.append_versions([new(package_id, good)])
    duplicate_id = StableId.new()

    with pytest.raises(PromptStoreError):
        store.append_versions(
            [
                NewPromptVersion(
                    duplicate_id,
                    package_id,
                    "1",
                    PromptEntry(PromptEntryKind.TASK, "a", "Neu", 0),
                    PromptVersionSource.UI,
                    CREATED,
                    "x",
                ),
                NewPromptVersion(
                    duplicate_id,  # same primary key: the second insert fails
                    package_id,
                    "1",
                    PromptEntry(PromptEntryKind.TASK, "b", "Text", 1),
                    PromptVersionSource.UI,
                    CREATED,
                    "x",
                ),
            ]
        )

    assert [v.entry.text for v in store.list_active(package_id, "1")] == ["Text"]


def test_directive_task_ids_and_option_defaults_roundtrip(prompts) -> None:
    store, _, package_id = prompts
    store.append_versions(
        [
            new(package_id, PromptEntry(PromptEntryKind.OPTION, "tone/dark", "d", 0, True)),
            new(
                package_id,
                PromptEntry(
                    PromptEntryKind.DIRECTIVE, "boundary", "Grenze", 0, task_ids=("a", "b")
                ),
            ),
        ]
    )

    active = {v.entry.kind: v.entry for v in store.list_active(package_id, "1")}

    assert active[PromptEntryKind.OPTION].is_default is True
    assert active[PromptEntryKind.DIRECTIVE].task_ids == ("a", "b")


def test_seeding_from_toml_into_postgres_is_the_story_prompt_source(prompts, tmp_path) -> None:
    from datetime import UTC, datetime

    from story_game.application import Success
    from story_game.application.prompt_management import (
        SeedPromptPackages,
        SeedPromptPackagesRequest,
    )

    store, catalog, package_id = prompts
    package_dir = tmp_path / package_id
    package_dir.mkdir()
    original_toml = (PROMPT_ROOT / "story.base" / "1.toml").read_text(encoding="utf-8")
    (package_dir / "1.toml").write_text(
        original_toml.replace('id = "story.base"', f'id = "{package_id}"', 1), encoding="utf-8"
    )
    source = FilePromptPackageCatalog(tmp_path)
    seed = SeedPromptPackages(source, store, store, StableId.new, lambda: datetime.now(UTC))

    first = seed.apply(SeedPromptPackagesRequest())
    second = seed.apply(SeedPromptPackagesRequest())

    assert isinstance(first, Success) and isinstance(second, Success)
    assert [r.package_id for r in first.data.seeded] == [package_id]
    assert second.data.seeded == ()
    assert catalog.load(package_id, "1") == source.load(package_id, "1")


def test_deactivating_an_entry_keeps_its_history_but_drops_it_from_the_active_set(prompts) -> None:
    store, catalog, package_id = prompts
    keep = PromptEntry(PromptEntryKind.TASK, "keep", "Bleibt", 0)
    retire = PromptEntry(PromptEntryKind.TASK, "retire", "Geht", 1)
    store.append_versions([new(package_id, keep), new(package_id, retire)])

    store.deactivate_entry(package_id, "1", PromptEntryKind.TASK, "retire")

    assert [v.entry.key for v in store.list_active(package_id, "1")] == ["keep"]
    history = store.list_history(package_id, "1", PromptEntryKind.TASK, "retire")
    assert [(v.entry.text, v.is_active) for v in history] == [("Geht", False)]


def _option(key, text="Text", position=0):
    return PromptEntry(PromptEntryKind.OPTION, key, text, position)


def test_an_archived_entry_is_listed_in_the_trash_with_its_newest_version(prompts) -> None:
    store, _, package_id = prompts
    store.append_versions([new(package_id, _option("tone/a", "Eins")), new(package_id, _option("tone/b"))])
    store.append_versions([new(package_id, _option("tone/a", "Zwei"), minutes=1)])

    store.deactivate_entry(package_id, "1", PromptEntryKind.OPTION, "tone/a")

    archived = store.list_archived(package_id, "1")
    assert [(v.entry.key, v.entry.text, v.is_active) for v in archived] == [("tone/a", "Zwei", False)]


def test_restoring_reactivates_the_newest_version_only(prompts) -> None:
    store, _, package_id = prompts
    store.append_versions([new(package_id, _option("tone/a", "Eins"))])
    store.append_versions([new(package_id, _option("tone/a", "Zwei"), minutes=1)])
    store.deactivate_entry(package_id, "1", PromptEntryKind.OPTION, "tone/a")

    store.restore_entry(package_id, "1", PromptEntryKind.OPTION, "tone/a")

    assert [(v.entry.text, v.is_active) for v in store.list_active(package_id, "1")] == [("Zwei", True)]
    assert store.list_archived(package_id, "1") == ()
    assert len(store.list_history(package_id, "1", PromptEntryKind.OPTION, "tone/a")) == 2


def test_purging_deletes_every_version_of_an_archived_entry(prompts) -> None:
    store, _, package_id = prompts
    store.append_versions([new(package_id, _option("tone/a", "Eins"))])
    store.append_versions([new(package_id, _option("tone/a", "Zwei"), minutes=1)])
    store.deactivate_entry(package_id, "1", PromptEntryKind.OPTION, "tone/a")

    store.purge_entry(package_id, "1", PromptEntryKind.OPTION, "tone/a")

    assert store.list_archived(package_id, "1") == ()
    assert store.list_history(package_id, "1", PromptEntryKind.OPTION, "tone/a") == ()


def test_purging_leaves_an_active_entry_alone(prompts) -> None:
    store, _, package_id = prompts
    store.append_versions([new(package_id, _option("tone/a"))])

    store.purge_entry(package_id, "1", PromptEntryKind.OPTION, "tone/a")

    assert [v.entry.key for v in store.list_active(package_id, "1")] == ["tone/a"]


def test_option_usage_follows_the_stored_game_configurations(postgres_store) -> None:
    from story_game.infrastructure.persistence.postgres import PostgresPromptOptionUsage
    from tests.ids import sid
    from tests.persistence.test_postgres_persistence import _delete_run, configuration, initial

    store, connections = postgres_store
    usage = PostgresPromptOptionUsage(connections)
    tone = f"usage_{uuid4().hex[:10]}"
    run_id = sid(f"usage-{uuid4()}")
    run, state = initial(run_id)
    state = replace(state, configuration=configuration(tone))

    assert usage.is_option_used("tone", tone) is False
    try:
        store.create(run, state)
        assert usage.is_option_used("tone", tone) is True
    finally:
        _delete_run(connections, run_id)
    assert usage.is_option_used("tone", tone) is False


def test_option_usage_is_only_defined_for_the_extensible_categories(postgres_store) -> None:
    from story_game.application.prompt_management import PromptStoreError
    from story_game.infrastructure.persistence.postgres import PostgresPromptOptionUsage

    _, connections = postgres_store

    with pytest.raises(PromptStoreError):
        PostgresPromptOptionUsage(connections).is_option_used("pacing", "slow")
