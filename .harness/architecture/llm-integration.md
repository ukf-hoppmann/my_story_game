# Binding LLM integration architecture

This file is the authoritative scoped architecture contract delegated by
`.harness/architecture-rules.md` for model invocation, prompt preparation,
provider and model adapters, and model-derived outputs. The root architecture
contract remains binding together with this scope.

## 1. Task-specific application contracts

- Every model-backed application capability MUST retain a domain-specific,
  application-owned port with a specifically typed request and success value.
- Application contracts MAY share a typed generic generation-call value, but a
  shared value MUST NOT replace task-specific ports or become a universal
  `LLMService` accepting arbitrary dictionaries or unrelated capabilities.
- A model invocation contract MUST bind one concrete request type to one
  concrete success-data type and MUST use the root architecture's closed
  `Success[DataT] | Failure[ErrorT]` result contract.
- Model and provider failures expected by application workflows MUST be exposed
  through an application-owned, provider-independent `LLMError` family.
  Provider exceptions, status codes, and raw response objects MUST NOT cross
  the port.

## 2. Application-owned prompt meaning

- The Application layer MUST decide which configuration, WorldState,
  StoryState, player input, generated prose, and other Domain information is
  relevant to one model invocation.
- Selected input MAY contain a complete Domain state or complete values selected
  from it. Code MUST NOT construct a partially populated canonical Domain value
  merely to represent prompt context.
- The Application layer MUST own the domain-specific prompt structure,
  including the role of system instructions, context, current input, and the
  expected task result.
- Adapter code MUST NOT select relevant game data, invent domain-specific
  prompt content, judge narrative plausibility, approve extracted changes, or
  decide which candidate changes enter canonical state.

## 3. Model selection and technical options

- Provider and model selection MAY be configurable through the UI and known to
  the backend, but use cases MUST NOT branch on a concrete provider, endpoint,
  SDK, or native response shape.
- A shared generation call MAY carry typed model selection and a place for
  generation options. Concrete option fields MUST be introduced only when their
  semantics and provider support are defined.
- Secrets MUST remain outside application requests, persisted game
  configuration, and repository model catalogs. Infrastructure MUST resolve
  them from the approved runtime secret source.

## 4. Infrastructure adapters and provider clients

- An infrastructure adapter MUST implement an application-owned model port and
  translate between its stable typed contract and one provider/model
  combination.
- A provider client SHOULD own only technical communication such as HTTP or SDK
  calls, authentication transport, timeouts, and raw provider request/response
  representations.
- Provider-format mapping and provider-error translation MUST remain in the
  provider adapter. Model-specific normalization MAY be added only when that
  model demonstrably differs from the standard output accepted by the port.
- The composition root MUST select the configured provider client, provider
  adapter, and optional model normalization. Application workflows MUST remain
  unaware of that concrete combination.
- An adapter MAY serialize the same stable input as JSON, named text sections,
  multiple messages, or a flat prompt. That choice MUST NOT change the
  domain-specific meaning of the request.

## 5. Story-generation boundary

- A Story-generation request MUST distinguish system prompts, relevant game and
  narrative configuration, relevant WorldState data, relevant StoryState data,
  and the current user prompt.
- The Application layer MUST assemble those values before invoking the model
  port. The adapter MUST only render and transport the prepared meaning.
- A successful Story-generation result MUST contain normalized story prose.
  Empty, incomplete, or technically invalid output MUST NOT be represented as a
  successful story.

## 5a. Story-initialization boundary

- A Story-initialization request MUST distinguish system prompts, relevant
  narrative configuration, the initial user prompt, and any caller-provided
  player-character seed. Because it executes before canonical WorldState and
  StoryState values exist, it MUST NOT require or fabricate either context.
- Player identity MUST be confirmed by the caller before it takes effect.
  Initial extraction MAY freely propose any narratively established character
  without designating a player role; the caller assigns player or non-player
  roles per character when confirming the resulting proposal (see §6b). Player
  control MUST result in exactly one confirmed player-character; director
  control MAY result in zero or more confirmed player-characters. First- and
  second-person narration MUST be invalid with director control.
- Player agency MUST affect only player control. Director control MUST describe
  user control over a scene or cast and MUST NOT be implemented as permission
  for the model to pre-empt a player character's decisions.
- Until those player-character and mode rules are implemented, the existing
  transient opening operation MUST NOT be exposed as a complete supported game
  start or persisted as one.
- The Application layer MUST assemble the request and create a complete
  transient StoryState from successful normalized opening prose. The provider
  adapter MUST only render and transport the prepared request.
- Story initialization alone MUST NOT persist a GameState. Canonical
  persistence remains unavailable until the separate initial WorldState
  extraction and validation workflow has completed successfully.

## 6. Extraction boundary

- An Extraction request MUST distinguish system prompts, the latest generated
  story text, and the relevant current WorldState data used for comparison.
- A successful Extraction result MUST contain typed, structured candidate data
  for its declared extraction scope. It MUST NOT masquerade as already approved
  canonical state.
- Technical parsing and structural schema validation MUST occur before the
  adapter returns success. Narrative plausibility, reference validity, Domain
  invariants, and change approval MUST remain Application/Domain concerns.
- Combined and specialized Extraction calls MAY use different prompts and input
  projections. Their orchestration MUST remain an Application workflow concern,
  and they MUST converge on one shared downstream validation, approval, and
  turn-completion path.
- When Extraction compares against an existing world, its projection MUST give
  every addressable object a short handle valid for that one call, and the
  model MUST address existing objects only through those handles. Labels are
  not sufficient because equally named entities are allowed. Stable IDs MUST
  NOT be used for this: they cost far more tokens, and a single mistyped
  identifier would discard an entire turn. Genuinely new objects keep using
  local references. The Application MUST resolve both forms and MUST reject a
  local reference that shadows a handle.
- Specialized partial results MAY remain transient while failed calls are
  handled, but they MUST enter the root architecture's canonical-state boundary
  only as one complete, validated turn result.
- Supporting evidence MAY be retained on transient review proposals. Initial
  Extraction MUST NOT be completed until canonical Fact and WorldRule values no
  longer require or persist that evidence, and model-produced evidence MUST NOT
  be copied into canonical state merely because a model produced it.

## 6a. Initial WorldState extraction

- Initial extraction MUST be a separate task-specific call after successful
  Story initialization. Its model input MUST distinguish Extraction system
  prompts, opening narration, response schema, language, perspective, and
  control mode. It carries no player-character seed and no reserved
  local-reference concept: the model addresses every character the same way,
  because which character (if any) becomes the player is decided later, at
  proposal confirmation (see §6b), not by the model.
- Opening narration MUST be the authoritative description of what happened.
  The original initial user prompt, Story prompt categories such as genre or
  tone, an existing WorldState, and an invented story history MUST NOT enter
  the initial Extraction model request.
- The structured model result MUST be limited to candidate entities, links,
  facts, and scene-location references, all using local entity references. It
  MUST NOT contain stable IDs, visibility, evidence, actor knowledge, world
  rules, or goals.
- The scene reference names where the opening is set. It is a separate
  statement from where entities are located: location links say where something
  is, the scene says where the narration currently looks. Both are required
  because director control MAY narrate a scene that the controlled character is
  not part of, so the scene MUST NOT be derived from any entity's location.
  The model MUST return the scene as ordered local references to extracted
  locations, most relevant first. The Application MUST map them to stable IDs
  and MUST reject references that are unknown, duplicated, or not locations.
- A model MAY return zero or more characters in every supported perspective,
  including one that narratively matches a caller-provided seed. Every
  extracted character MUST be assigned the neutral actor role by the
  Application at this stage; no character is created, altered, or excluded by
  the Application on the model's behalf here. Promoting a character to the
  player role is exclusively a §6b confirmation decision.
- The adapter MUST perform provider JSON mapping and strict structural schema
  validation. The Application MUST resolve local references, create stable IDs,
  reject duplicate local references, and construct one complete WorldState
  under Domain invariants. Any model, schema, reference, or Domain failure MUST
  return a typed error and MUST NOT expose a partial WorldState.
- Initial extraction MUST produce empty knowledge, rules, and goals. It MUST use
  the existing public visibility default without asking the model to classify
  visibility. That default MUST NOT be treated as an implemented UI access
  policy.
- Initial extraction MUST NOT retry automatically or persist any result. The
  initial orchestration MAY return StoryState and WorldState only after both
  task-specific operations have succeeded.

## 6b. Run-proposal confirmation

- The complete result of Story initialization and initial WorldState
  extraction MUST be held as a transient, caller-owned proposal before any
  GameRun is persisted. Generating a proposal MUST NOT create a GameRun,
  GameRunMember, or canonical GameState.
- A proposal MUST be addressable only by its own caller (issuer/subject). It
  MAY expire after a bounded time. An unknown, expired, or not-owned proposal
  MUST be rejected with the same typed failure a caller cannot distinguish
  from "never existed", so a proposal's existence is not observable by anyone
  but its owner.
- Confirming a proposal is the one point where the caller assigns the player
  or non-player role per extracted character, and may exclude any extracted
  character or item from the resulting world. Confirmation MUST NOT accept
  arbitrary caller-supplied WorldState content: it MAY only select and role-
  assign among what the cached proposal already contains.
- Dropping a character or item at confirmation MUST also drop every link and
  fact that referenced it, so confirmation can never produce the same class of
  dangling-reference failure Initial extraction guards against. Confirmation
  MUST still enforce "exactly one confirmed player-character" for player
  control and "zero or more" for director control before persistence.
- Only a successful confirmation MAY persist a GameRun; it MUST do so exactly
  as the existing DRAFT-at-revision-one contract already requires. The
  proposal MUST be discarded once successfully confirmed.

## 7. Extensibility without a universal model service

- Shared generation infrastructure MUST NOT assume that every success value is
  text or JSON. A later image-generation capability MAY define its own typed
  request, success value, error family, and port while reusing suitable generic
  generation-call building blocks.
- Future modality support MUST NOT weaken the task-specific port requirement or
  force text, structured Extraction, and binary/image workflows through an
  untyped universal interface.

## 8. Verification

- Model-port tests MUST prove that raw provider response objects and exceptions
  do not cross into Application code.
- Adapter tests MUST cover request mapping, success normalization, empty and
  malformed output, and every provider-error category that affects workflow
  decisions.
- Application tests MUST prove that prompt-context selection and
  domain-specific prompt composition remain outside adapters.
- Extraction workflow tests MUST cover structural failure, semantic rejection,
  cross-result aggregation where used, and the absence of partial canonical
  state writes.
- Story-initialization tests MUST cover every supported perspective/control
  combination, required or forbidden player-character seeds, and the absence
  of a model call after configuration rejection.
- Initial-Extraction tests MUST cover empty candidate collections, characters
  in every supported perspective coming back with the neutral actor role,
  duplicate local-reference rejection, other local-reference failures, Domain
  rejection, empty knowledge, rules, and goals, and scene references that are
  unknown, duplicated, or point at a non-location.
- Run-proposal-confirmation tests MUST cover role assignment per confirmed
  character, cascading removal of dependent links and facts, the "exactly one
  confirmed player-character" invariant for player control, rejection of an
  unknown/expired/not-owned proposal without distinguishing the three, and
  that only a successful confirmation persists a GameRun and discards the
  proposal.
- Architecture tests MUST enforce inward dependency direction for model ports,
  adapters, provider clients, and composition.
