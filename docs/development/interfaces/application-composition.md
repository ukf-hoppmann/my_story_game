# Interface: Application composition

## Purpose

Shared vocabulary and structural conventions for composing and executing application operations: how the object graph is built (Composition Root, Composition Builder), how operations are structured (Top-Level Composite, Composite Level X, Leaf) and how they are called (Operation Contract). Use these terms in plans, reviews, code comments and communication. Owner: application layer (`Backend/src/story_game/application/`) and the composition root in the API layer (`Backend/src/story_game/api/app.py`). The binding rules behind this vocabulary are in [../architecture.md](../architecture.md) (rules 2–4 and 9–10).

## Use

### Vocabulary

| Level / role | Name | Task | Example |
|---|---|---|---|
| Wiring outside execution | `Composition Root` | Creates and connects the object graph with concrete implementations. | `create_app` and its `lifespan` in `api/app.py` |
| Building block for that wiring | `Composition Builder` | Builds one operation graph from operations and their dependencies. Project-internal role name; in general terms a factory or dependency-wiring module. It is not the common interface of executable operations. | `_compose_propose_game_run` creates `ProposeGameRun` with its collaborators |
| Topmost executable level | `Top-Level Composite` | Entry point of a complete business workflow. | `ProposeGameRun`, `PlayStoryTurn` |
| Nested executable level | `Composite Level X` | Composes and delegates to further operations. | `InitializeStory` (Composite Level 1) |
| Single executable level | `Leaf` | Executes one concrete business or technical step. | `GenerateInitialStoryState` |
| Shared execution contract | `Operation Contract` | The uniform entry point `apply(request)`. | `Operation` protocol in `application/contracts.py` |
| Dependency passed via constructor | `Injected Collaborator` | Used by an operation but not created by it. | `story_generation` parameter of `InitializeStory` |
| Call of a subordinate operation | `Delegation` | Passes typed input to the next operation level. | `InitializeStory.apply(...)` called by `ProposeGameRun` |
| Dependency passing mechanism | `Constructor Injection` | An operation receives and stores its collaborators before execution. | `InitializeStory(story_generation, world_extraction, …)` |

`Composition Root` and `Composition Builder` belong to creating and wiring the object graph. `Top-Level Composite`, `Composite Level X` and `Leaf` describe the application structure that is executed later.

### Operation Contract

Every executable application operation provides:

```python
def apply(self, request: RequestT) -> OperationResult[DataT, ErrorT]: ...
```

```python
@dataclass(frozen=True, slots=True)
class Success(Generic[DataT]):
    data: DataT

@dataclass(frozen=True, slots=True)
class Failure(Generic[ErrorT]):
    error: ErrorT

OperationResult = Success[DataT] | Failure[ErrorT]
```

(`Operation[InputT, DataT, ErrorT]` is the `Protocol` in `application/contracts.py`.)

Rules:

- The constructor is not part of the execution contract. It performs `Constructor Injection`; `apply` runs the already prepared operation.
- `apply` must not become a hidden service locator or dependency factory.
- Expected outcomes use the closed result `Success[DataT] | Failure[ErrorT]`; each operation has its own typed request and typed error values. No generic response object with optional `data`/`error`/status fields.
- Input, execution and result are typed independently of the hierarchy level.
- Unexpected programming defects are not converted into `Failure`.

### Example: story initialization

```text
Composition Root (api/app.py: create_app / lifespan)
└── Composition Builder (_compose_propose_game_run)
    └── Top-Level Composite: ProposeGameRun
        └── Composite Level 1: InitializeStory
            ├── Leaf: GenerateInitialStoryState      (story_generation)
            ├── Leaf: ExtractInitialWorldState       (world_extraction; world tracking on)
            └── Leaf: BuildSeedWorldState            (seed_world; world tracking off)
```

`ProposeGameRun` additionally receives the `InitialProposalStore` port (a port, not a `Leaf`) and calls `save` on it after `InitializeStory` succeeds.

Runtime flow:

```text
ProposeGameRun.apply(...)
├── delegates to InitializeStory.apply(...)
│   ├── delegates to GenerateInitialStoryState.apply(...)
│   └── delegates to ExtractInitialWorldState.apply(...)     if WorldTrackingPolicy.extraction_enabled()
│       or BuildSeedWorldState.apply(...)                    otherwise
└── saves the owner-bound proposal transiently (InitialProposalStore.save)
```

`ConfirmGameRunProposal` is a separate Top-Level Composite: it loads a valid proposal, applies the caller's decisions and only then delegates to `CreateGameRun`. No canonical game state exists between proposal and confirmation. `StartPlaythrough` delegates to `LoadGame` and `CreateGameRun`.

`PlayStoryTurn` is the Top-Level Composite of a turn. Its visible order: `LoadGame` (membership) → status must be `active` → select context → generate story → (when extraction is enabled) extract and approve changes, otherwise an empty change set → optional summary → `CommitCompletedTurn`. The decision whether extraction runs belongs to the `WorldTrackingPolicy`, not to the Composition Builder.

### Where things live

| Concern | Location |
|---|---|
| Operation Contract (`Success`, `Failure`, `OperationResult`, `Operation`) | `application/contracts.py` |
| Ports owned by the application | `application/ports.py` and the `ports.py` of each operation package |
| Composition Builders | `_compose_*` functions in `api/app.py`; the application-facing result is the frozen dataclass `ApiDependencies` in `api/dependencies.py` |
| Startup order in `lifespan` | optional schema migration (`STORY_GAME_AUTO_MIGRATE`), prompt seed, model-settings seed, proposal store, world-tracking store, LLM clients, optional scene images, then the `_compose_*` calls |

### Lifecycle and removal

Removable data follows `active → archived → purged` ([../architecture.md](../architecture.md), rule 10).

| Term | Meaning | Example (`Leaf`) |
|---|---|---|
| `Archive` | Reversible deactivation (trash); history is kept. | `ArchivePromptOption` |
| `Restore` | Take an item out of the trash. | `RestorePromptOption` |
| `Purge` | Permanent deletion including history; only for archived items. | `PurgePromptOption` |

A bulk operation such as `RemovePromptOptions` is a `Composite Level 1` over these three leaves. It receives `RemovalMode` (`ARCHIVE` or `PURGE`) and the scope as typed input; the Composition Root wires only the leaves. Each item yields a typed outcome (`RemovalStatus`: `done`, `in_use`, `protected`, `not_archived`, `not_found`). Blocking rules live in the leaves, so single and bulk paths are guarded identically.

### Communication phrases

These formulations are unambiguous in architecture discussions:

- "The problem lies in the `Top-Level Composite`."
- "`InitializeStory` is a `Composite Level 1`."
- "The model request is a `Leaf`."
- "The dependency is passed through `Constructor Injection` as an `Injected Collaborator`."
- "The next level is delegated to through the `Operation Contract` with `apply`."
- "The concrete wiring belongs in the `Composition Builder` inside the `Composition Root`."

## Behavior

- Composite operations define the business-visible order. A Leaf executes exactly one concrete step. A `Composition Root` or `Composition Builder` must not fix that order as a hidden workflow in a constructor.
- A policy decides *when* an action happens (for example whether world extraction runs); a workflow decides the explicit order; an operation executes one step ([../architecture.md](../architecture.md), rule 4). Optional branches are driven by explicit policies or typed input, not by a family of factories.
- Only an explicit composition root may import both outer adapters and infrastructure ([../architecture.md](../architecture.md), rule 3). Operations never construct their adapters themselves.
- Failures of ports and adapters are translated into application-owned typed failures before they reach the operation's result ([../architecture.md](../architecture.md), rules 2 and 3).

## Related

- [../architecture.md](../architecture.md): rules 2 (typed operation contract), 3 (ports and adapters), 4 (composition, workflow, policy), 9 (naming, points here) and 10 (lifecycle and removal).
- [../architecture/llm-integration.md](../architecture/llm-integration.md): the LLM-facing operations and the world-tracking policy.
- [./http-api.md](./http-api.md): the endpoints that call the Top-Level Composites.
- [./persistence.md](./persistence.md): persistence ports behind `CreateGameRun`, `CommitCompletedTurn`.
- [./domain-model.md](./domain-model.md): the domain types the operations exchange.
- Code: [contracts.py](../../../Backend/src/story_game/application/contracts.py), [propose_game_run.py](../../../Backend/src/story_game/application/propose_game_run.py), [initialize_story.py](../../../Backend/src/story_game/application/initialize_story.py), [play_story_turn.py](../../../Backend/src/story_game/application/play_story_turn.py), [prompt_management/operations.py](../../../Backend/src/story_game/application/prompt_management/operations.py), [api/app.py](../../../Backend/src/story_game/api/app.py).
