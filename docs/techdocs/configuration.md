# Konfiguration

<!-- Jede Einstellung mit Typ, Standardwert, Pflicht und Wirkung. -->

Konfigurationsdateien werden beim Start gelesen; Änderungen brauchen einen
Backend-Neustart. Ausnahme: Prompts und Modellwahl je Task liegen nach dem
ersten Start in der Datenbank und werden in `/settings` (Rolle `admin`)
geändert, ohne Neustart. Die TOML-Werte dafür sind nur Vorgabe und Reset-Quelle.

## Umgebungsvariablen des Backends

Gesetzt in `compose.yaml`; Standardwerte gelten ohne Docker.

| Einstellung | Typ | Standard | Pflicht | Wirkung |
|---|---|---|---|---|
| `STORY_GAME_POSTGRES_DSN` | Text | `postgresql://story_game:story_game_dev@localhost:5433/story_game` | ja im Betrieb | Verbindung zu PostgreSQL |
| `STORY_GAME_AUTO_MIGRATE` | Boolesch | `true` | nein | Migrationen beim Start ausführen |
| `STORY_GAME_PROMPT_ROOT` | Pfad | `prompts` | nein | Ordner der Prompt-Pakete (Quelle für den ersten Import in die Datenbank) |
| `STORY_GAME_CONFIG_PATH` | Pfad | `configs/app.toml` | nein | Anwendungskonfiguration |
| `STORY_GAME_LLM_CONFIG_PATH` | Pfad | `configs/llm.toml` | nein | LLM-Katalog |
| `STORY_GAME_CORS_ALLOWED_ORIGINS` | Liste (Komma) | `http://localhost:5173` | nein | Erlaubte Browser-Origins (im Compose: `http://storygame.localhost`) |
| `STORY_GAME_KEYCLOAK_ISSUER` | URL | `http://localhost:8081/realms/story-game` | ja im Betrieb | Vertrauter Realm; muss dem `iss` des Tokens entsprechen |
| `STORY_GAME_KEYCLOAK_AUDIENCE` | Text | `story-game-frontend` | nein | Erwarteter `aud`-Claim; leer schaltet die Prüfung ab |
| `STORY_GAME_KEYCLOAK_JWKS_URI` | URL | `<issuer>/protocol/openid-connect/certs` | nein | Quelle der Signaturschlüssel, wenn Backend und Browser Keycloak unter verschiedenen Adressen erreichen |
| `STORY_GAME_LOG_MODE` | `prod` oder `debug` | Wert aus `app.toml` | nein | Überschreibt `[logging] mode` |
| `STORY_GAME_LOG_LEVEL` | Text | Wert aus `app.toml` | nein | Überschreibt `[logging] level` (nur `prod`) |
| `STORY_GAME_API_TITLE`, `STORY_GAME_API_VERSION` | Text | `Story Game API`, `0.1.0` | nein | Titel und Version im OpenAPI-Schema |
| `STORY_GAME_DEV_ISSUER`, `STORY_GAME_DEV_SUBJECT` | Text | `https://dev.story-game.local/realm`, `dev-user` | nein | Nur für Tests, die die Identität überschreiben |

## Backend/configs/app.toml

| Einstellung | Typ | Standard | Pflicht | Wirkung |
|---|---|---|---|---|
| `[logging] mode` | `prod` / `debug` | `debug` im Repo | nein | `debug` loggt zusätzlich Rohprompts und Zwischenwerte, nie gegen reale Spieler-Umgebungen ([Logging](../human/operations/logging.md)) |
| `[logging] level` | Text | `INFO` | nein | Log-Level in `prod` |
| `[logging] file_path` | Pfad | `logs/story-game.log` | nein | Logdatei |
| `[logging] file_max_bytes` | Zahl | `10485760` | nein | Größe, ab der rotiert wird |
| `[logging] file_backup_count` | Zahl | `5` | nein | Anzahl Backups |
| `[story_summary] interval` | Zahl | `1` | nein | Wie viele Züge ein neues Zusammenfassungssegment abdeckt |
| `[story_summary] context_segment_count` | Zahl | `2` | nein | Wie viele neueste Segmente in den Erzählkontext gehen |
| `[scene_image] enabled` | Boolesch | im Code `false`, im Repo `true` | nein | Szenenbilder ein/aus; aus: Capability meldet `enabled: false`, andere Endpunkte 409 |
| `[scene_image] provider` | Text | `modal` | nein | Bildanbieter |
| `[scene_image] turn_window` | Zahl | `3` | nein | Aus wie vielen letzten Zügen der Bildprompt entsteht |
| `[scene_image] width`, `height` | Zahl | `1024` | nein | Bildgröße |
| `[scene_image] refine` | Boolesch | im Code `false`, im Repo `true` | nein | Verfeinerung standardmäßig an; pro Bild abwählbar |
| `[scene_image] refine_model` | Text | `juggernaut-xl-ragnarok` | nein | SDXL-Modell der Verfeinerung |
| `[scene_image] refine_strength` | Zahl 0,1–0,8 | `0.35` | nein | Wie stark die Verfeinerung ändern darf |
| `[scene_image] compact_prompt_max_words` | Zahl | `60` | nein | Maximale Länge des Prompts der Verfeinerung |
| `[scene_image.modal] url`, `control_url` | URL | – | ja bei `enabled = true` | Modal-Endpunkte für Rendern und Modellliste |
| `[scene_image.modal] model` | Text | `z-image-turbo` | ja bei `enabled = true` | Standard-Bildmodell |
| `[scene_image.modal] timeout_seconds` | Zahl | `900` | nein | Zeitlimit je Erzeugung |
| `[scene_image.modal] negative_prompt`, `refine_negative_prompt` | Text | leer | nein | Negativprompts |

Details: [Szenenbilder betreiben](../human/operations/szenenbilder.md).

## Backend/configs/llm.toml

Provider, Modellkatalog und Vorgaben je Task. Provider, URLs und der Katalog
werden bei jedem Modellaufruf frisch gelesen; die Wahl je Task steht nach dem
ersten Start in der Datenbank.

| Einstellung | Typ | Standard | Pflicht | Wirkung |
|---|---|---|---|---|
| `[providers.<id>] base_url` | URL | LM Studio `http://host.docker.internal:1234/v1`, Groq, Gemini | ja je Provider | Endpunkt des OpenAI-kompatiblen Providers |
| `[providers.<id>] timeout_seconds` | Zahl | 600 (LM Studio), 60 (Groq, Gemini) | nein | Zeitlimit je Aufruf |
| `[task_models] <task>` | Katalog-ID | `model.<task>.default` | ja je Task | Vorgabemodell für `story`, `extraction`, `summary`, `scene_image`; nur Seed und Reset-Quelle |
| `[generation_options.<task>] temperature` | Zahl | 0,5 / 0,3 / 0,5 / 0,7 | nein | Vorgabe-Temperatur; nur Seed und Reset-Quelle |
| `[[models]] id`, `task`, `provider_id`, `model_id` | Text | – | ja je Modell | Katalogeintrag; nur diese Modelle sind in `/settings` wählbar |

Anleitungen je Anbieter: [LM Studio](../human/operations/lmstudio.md),
[Groq](../human/operations/groq.md), [Gemini](../human/operations/gemini.md).

## Geheimnisse (nicht versioniert)

| Datei | Inhalt | Pflicht | Wirkung |
|---|---|---|---|
| `Backend/configs/llm.secrets.toml` | `[providers.groq] api_key`, `[providers.gemini] api_key` | nur für diese Provider | API-Keys; Vorlage `llm.secrets.toml.example` |
| `Backend/configs/scene_image.secrets.toml` | `[modal] key`, `[modal] secret` | bei Szenenbildern | Modal-Proxy-Token (`Authorization: Bearer <key>.<secret>`); Vorlage `scene_image.secrets.toml.example` |

## Compose (`compose.yaml`, Umgebungsvariablen des Hosts)

| Einstellung | Typ | Standard | Pflicht | Wirkung |
|---|---|---|---|---|
| `POSTGRES_HOST_PORT` | Zahl | `5433` | nein | Host-Port der Datenbank |
| `KEYCLOAK_HOST_PORT` | Zahl | `8081` | nein | Host-Port von Keycloak |
| `BACKEND_HOST_PORT` | Zahl | `8001` | nein | Host-Port des Backends |
| `FRONTEND_HOST_PORT` | Zahl | `5173` | nein | Host-Port des Frontends (nur 127.0.0.1) |
| `PROXY_HOST_PORT` | Zahl | `80` | nein | Host-Port des nginx-Proxys |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Text | `story_game`, `story_game_dev`, `story_game` | nein | Zugang zur lokalen Datenbank |
| `FRONTEND_NODE_TAG` | Text | `20-alpine` | nein | Node-Image des Frontends |

## Frontend

| Einstellung | Typ | Standard | Pflicht | Wirkung |
|---|---|---|---|---|
| `VITE_API_BASE_URL` | URL | `http://backend.storygame.localhost` im Compose | ja im Betrieb | Basis-URL der API |

## Keycloak

Realm `story-game` mit Client `story-game-frontend` und der Realm-Rolle
`admin`, importiert aus `configs/keycloak`. Ein bereits importiertes Realm
muss die Rolle einmalig von Hand erhalten ([Keycloak](../human/operations/keycloak.md)).
