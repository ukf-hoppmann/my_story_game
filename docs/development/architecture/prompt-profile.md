# Scope: prompt-profile

<!-- Rules for the prompt profile of a game and the prompt package it selects
from. Applies in addition to architecture.md and
architecture/llm-integration.md. -->

## Responsibilities

| Concern | Owner | Others do | Others don't | Details |
|---|---|---|---|---|
| Structure of the profile | Domain (`PromptProfile`) | Construct it with non-empty values | Validate option IDs in the Domain | [domain-model](../interfaces/domain-model.md) |
| Validity of option IDs | Application (`prompt_profile_validation`) | Reject unknown IDs with a typed failure | Fall back silently to a default | [domain-model](../interfaces/domain-model.md) |
| Projection into prompts | Application (`prompt_selection`) | Use the resolvers | Select categories in an adapter | [llm-integration](../interfaces/llm-integration.md) |
| Loading prompt packages | Infrastructure file adapter behind an application-owned catalog port | Read packages through the port | Parse package files in the Application | [llm-integration](../interfaces/llm-integration.md) |

## Rules

1. The Domain MUST validate only the structure of a prompt profile. The
   Application MUST validate every option ID against the prompt package and
   MUST NOT fall back silently when an ID is unknown.
2. An unset `tone` MUST stay `None` and render no prompt text; it MUST NOT be
   replaced by a catalog option such as `balanced`. `length` defaults to
   `standard`. Defaults only pre-fill the choice; the full profile is stored
   with the run.
3. `player_agency` MUST be stored with every profile but MUST be projected into
   prompts only for player control.
4. Extraction prompts MUST use only the task `worldstate_extraction` and the
   option `extraction.combined` of the package. Story categories MUST NOT reach
   Extraction, and `extraction` MUST NOT be part of the stored profile.
5. The prompt-package loader MUST fail closed: invalid TOML, unknown or missing
   fields, duplicate IDs, an invalid default, path components in IDs, and
   directives for unknown tasks MUST be rejected, and a missing package MUST be
   distinguishable from an invalid one. The catalog port is owned by the
   Application; the file adapter lives in Infrastructure.
