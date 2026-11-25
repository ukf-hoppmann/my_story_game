# Interfaces

<!-- Index of the interface docs for the AI: how things are done (APIs, file
formats, shared building blocks). Always English and current-state only. One
line per file below interfaces/, each with a link; add the line when you add
the file. A file X.md may sit next to a folder X/ with its parts. Catalogs
list the reusable building blocks of one owner (start them from catalog.md),
single interfaces start from interface.md. What is mandatory is decided in
architecture.md and its scopes, not here. -->

Search the catalogs before building something new.

| File | Covers |
|---|---|
| [catalog-domain.md](interfaces/catalog-domain.md) | Catalog of the reusable building blocks of the Domain layer |
| [catalog-application.md](interfaces/catalog-application.md) | Catalog of the application operations, ports, and the result contract |
| [catalog-infrastructure.md](interfaces/catalog-infrastructure.md) | Catalog of the persistence, model, image, and configuration adapters and the composition root |
| [catalog-api.md](interfaces/catalog-api.md) | Catalog of the HTTP routers, schemas, mappers, authentication, and error mapping |
| [catalog-frontend.md](interfaces/catalog-frontend.md) | Catalog of the web frontend building blocks |
| [http-api.md](interfaces/http-api.md) | Endpoints, request and response shapes, access rules, and error codes of the `/api/v1` HTTP API |
| [domain-model.md](interfaces/domain-model.md) | The canonical game state, its invariants, the prompt profile, and the proposal and approval boundary |
| [persistence.md](interfaces/persistence.md) | PostgreSQL tables, revision and append-only patterns, write boundaries, and the local database |
| [application-composition.md](interfaces/application-composition.md) | Naming vocabulary and structure of application composition: Operation Contract, Composition Root, Composites, Leaves |
| [llm-integration.md](interfaces/llm-integration.md) | Model ports, error family, extraction schemas, prompt packages, `llm.toml`, and the story-turn pipeline |
