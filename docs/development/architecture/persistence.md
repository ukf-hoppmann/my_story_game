# Scope: persistence

<!-- Rules for the persistence adapters of the game state. Applies in addition
to architecture.md (rules 3, 5, 10). -->

## Responsibilities

| Concern | Owner | Others do | Others don't | Details |
|---|---|---|---|---|
| Atomic turn commit | `commit_turn` in the Postgres store | Hand over one completed turn with its base revision | Write turn, revision, changes or summary segment separately | [persistence](../interfaces/persistence.md) |
| Revisioned world snapshot | Postgres snapshot reader and writer | Read and write whole revisions through the store | Update a world row in place | [persistence](../interfaces/persistence.md) |
| Append-only story text | Postgres story writer | Append a turn or a summary segment once | Rewrite earlier turns or segments | [persistence](../interfaces/persistence.md) |

## Rules

1. A turn MUST be committed atomically: the `StoryTurn`, the new revision, the
   approved changes and the summary segment belong to one transaction, guarded
   by a lock and a base-revision check. The adapter MUST NOT call a model
   inside that transaction.
2. A failed or crashed turn MUST leave no trace. Play resumes from the previous
   revision. A half-finished turn workflow MUST NOT be persisted or resumed,
   and workflow status MUST NOT be part of `GameRun` or `GameState`.
3. Turn text and summary segments MUST be written once and only appended. Only
   the world snapshot is stored per revision, as a full snapshot.
4. Persistence-adapter failures MUST be translated to application-owned
   failures before they reach a use case (root rule 3).

## Required on use

| Uses | Read |
|---|---|
| `commit_turn`, `CompletedTurnPersistenceRequest` | `docs/development/interfaces/persistence.md` |
