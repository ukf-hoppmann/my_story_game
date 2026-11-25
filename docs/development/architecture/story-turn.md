# Scope: story-turn

<!-- Rules for the story-turn workflow: context selection, turn extraction,
change approval, summary, and the hand-over to the atomic commit. Applies in
addition to architecture.md and architecture/llm-integration.md. -->

## Responsibilities

| Concern | Owner | Others do | Others don't | Details |
|---|---|---|---|---|
| Story context of a turn | Application (`story_turn_context` and its `select_*` steps) | Use the selected context to build the prompt | Filter the context by visibility, select context in an adapter | [catalog-application](../interfaces/catalog-application.md) |
| Turn proposal approval | `ApproveStoryTurnChanges` | Pass every extraction variant through it | Approve or write state anywhere else | [llm-integration](../interfaces/llm-integration.md) |
| Turn order and summary | `PlayStoryTurn` | Call it as the one workflow of a turn | Reorder or split a turn across callers | [llm-integration](../interfaces/llm-integration.md) |
| Atomic turn commit | Persistence adapter behind the application port | Hand over one completed turn | Commit parts of a turn separately | [persistence](../interfaces/persistence.md) |

## Rules

1. Context selection MUST NOT filter by `Visibility`. A `director_only` fact or
   goal enters the story prompt like any other, because the model has to be
   able to steer towards what the player does not know yet. Visibility is a
   concern of the prose and of UI read paths, not of context selection.
2. Context selection MUST be a deterministic pipeline without a model call:
   always-included frame, mentioned entities, scene locations, one-hop
   expansion, referenced facts, knowledge and goals, then a budget by counts.
   When the budget trims anything it MUST set the `truncated` flag and MUST
   drop what points at a trimmed entity. A token budget is a concern of the
   later request projection, not of selection.
3. Turn Extraction MUST NOT receive the player's input. The narration is the
   source of truth for what happened, not what the player attempted.
4. Turn approval is one all-or-nothing funnel shared by every extraction
   variant. It resolves handles and local references, orders removals before
   additions, and checks the Domain invariants before anything is written. A
   rejected proposal is discarded as a whole. Unknown references are the one
   transitional exception: only the offending item is dropped and reported.
5. A failed summary MUST NOT abort or discard the turn. It is reported as a
   transient `summary_failure` next to the committed turn.
6. All model calls of a turn (story, extraction, summary) MUST complete before
   the commit. The commit is one call to the persistence port (see scope
   `persistence`).
