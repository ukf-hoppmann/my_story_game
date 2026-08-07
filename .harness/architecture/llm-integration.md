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
- Specialized partial results MAY remain transient while failed calls are
  handled, but they MUST enter the root architecture's canonical-state boundary
  only as one complete, validated turn result.

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
- Architecture tests MUST enforce inward dependency direction for model ports,
  adapters, provider clients, and composition.
