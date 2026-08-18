# HTTP-API

Die API deckt den vollständigen Lauf-Lebenszyklus ab: eine Vorlage (`DRAFT`)
erzeugen, sie als unabhängiges aktives Spiel (`ACTIVE`) abzweigen, einen Zug
spielen und beides laden oder auflisten. Es gibt noch keine Authentifizierung
— jeder Aufruf agiert als eine feste, konfigurierbare Entwicklungsidentität
(siehe unten), bis Keycloak angebunden ist.

## Endpunkte

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/health` | Erreichbarkeit prüfen |
| `GET` | `/api/v1/runs` | Eigene `DRAFT`-Vorlagen und `ACTIVE`-Spiele auflisten |
| `GET` | `/api/v1/runs/{run_id}` | Aktuellen oder historischen (`?revision=N`) GameRun/GameState laden |
| `POST` | `/api/v1/runs` | Neue `DRAFT`-Vorlage aus Initialprompt und Modus erzeugen |
| `POST` | `/api/v1/runs/{run_id}/playthroughs` | Eine `DRAFT`-Vorlage als neues unabhängiges `ACTIVE`-Spiel abzweigen |
| `POST` | `/api/v1/runs/{run_id}/turns` | Einen Zug in einem `ACTIVE`-Spiel spielen |

## Vorlage und abgespieltes Spiel

`POST /api/v1/runs` erzeugt über `InitializeGameRun` eine vollständige
Eröffnung (Story-Generierung + initiale WorldState-Extraktion) und legt sie
als `GameRun` im Status `DRAFT` mit Revision 1 an. Diese Vorlage bleibt
unverändert und kann beliebig oft erneut abgezweigt werden.

`POST /api/v1/runs/{run_id}/playthroughs` kopiert eine `DRAFT`-Vorlage in
einen neuen, unabhängigen `GameRun` im Status `ACTIVE` (ebenfalls Revision 1,
eigene `run_id`). Nur `DRAFT`-Läufe können abgezweigt werden; der Versuch,
einen bereits aktiven Lauf erneut abzuzweigen, ergibt HTTP 409
(`error = "playthrough_source_not_draft"`).

`POST /api/v1/runs/{run_id}/turns` spielt einen Zug ausschließlich in einem
`ACTIVE`-Lauf. Gegen eine `DRAFT`-Vorlage ergibt das HTTP 409
(`error = "run_not_active"`).

## Anfrage- und Antwortformen

`POST /api/v1/runs` verlangt `run_name`, `initial_prompt`, `control_mode`
(`"player"` oder `"director"`) und im Player Mode genau ein
`player_character` (`name`, optional `description`). Die API verwendet
dafür eine feste serverseitige `GameConfiguration`
(`api/default_configuration.py`) — es gibt noch keine
Konfigurations-Auswahl über die API; nur `control_mode` wird aus der
Anfrage übernommen.

`POST /api/v1/runs/{run_id}/turns` verlangt nur `player_input` und liefert
`TurnResultModel`: den vollständigen aktualisierten `GameStateModel` sowie
`proposed_change_count`, `summary_failed` und optional
`summary_failure_message` als transiente Diagnose — ein Fehlschlag der
Zusammenfassung lässt den Zug selbst unangetastet (siehe TASK-023).

`GET /api/v1/runs` liefert `RunSummaryModel`-Einträge (`id`, `name`,
`status`, `current_revision`, `game_role`, `updated_at`) ohne vollen
WorldState, damit eine Liste nicht pro Zeile einen kompletten Weltsnapshot
lädt. `GET /api/v1/runs/{run_id}` liefert weiterhin das vollständige
`GameDocument` (siehe unten).

Das gemeinsame Transportdokument für Init-, Playthrough- und Load-Antworten
heißt `GameDocument` und enthält sowohl `game_run` als auch `game_state`. Der
GameState enthält die komplette `GameConfiguration`, den `WorldState`
einschließlich Goals und den `StoryState`. Fremde Felder und fachlich
inkonsistente IDs werden abgewiesen.

`world.scene_location_ids` ist eine geordnete Liste von Orts-UUIDs und benennt,
wo die Erzählung spielt; der erste Eintrag ist der Hauptschauplatz. Die Liste
ist getrennt von den `located_in`-Beziehungen: diese sagen, wo eine Entität ist,
jene, wohin die Erzählung blickt. IDs, die keinen vorhandenen Ort bezeichnen,
sowie Duplikate werden abgewiesen.

`schema_version` kennzeichnet den Aufbau des Transportdokuments und steigt nur
bei brechenden Änderungen: entfernten oder umbenannten Feldern, geänderten Typen
oder geänderter Bedeutung eines Feldes. Ein zusätzliches Feld mit Standardwert
ist dagegen rein additiv — ältere Clients ignorieren es, und ältere Dokumente
bleiben ohne Anpassung gültig.

Alle internen IDs werden im OpenAPI-Schema als `string` mit `format: uuid`
ausgewiesen und im JSON in kanonischer UUID-Schreibweise übertragen. Das gilt
auch für `run_id` im Pfad; eine nicht als UUID parsebare ID führt zu HTTP 422.
`game_run.name` ist der lesbare Anzeigename und unabhängig von der technischen
ID. Keycloak-, Prompt-Paket- und Promptprofil-Kennungen bleiben Text.

## Feste Entwicklungsidentität

Jeder Aufruf agiert als dieselbe feste Identität
(`ApiSettings.dev_issuer`/`dev_subject`, überschreibbar über
`STORY_GAME_DEV_ISSUER`/`STORY_GAME_DEV_SUBJECT`), aufgelöst über
`get_current_initiator` in `api/dependencies.py`. Das ist bewusst eine
einzige austauschbare Funktion: der Wechsel auf echtes
Keycloak-Token-Parsing ändert später nur ihren Rumpf, keine Router oder
Schemas. Bis dahin gehört jeder erzeugte Lauf derselben Identität, und
`GET /api/v1/runs` zeigt ausschließlich deren Läufe.

## Fehlerantworten

Jede Fehlerantwort hat die Form `{"error": <code>, "detail": <Text>, ...}`.
Über die bereits dokumentierten Zustandsfehler hinaus (`not_found`,
`revision_conflict`, `domain_validation_failed`, `invalid_prompt_selection`,
`persistence_unavailable`, …) kennt die Lauf-API zusätzlich:

| HTTP | `error` | Bedeutung |
| --- | --- | --- |
| 403 | `not_a_run_member` | Die aufrufende Identität gehört nicht zum GameRun |
| 409 | `run_not_active` | Ein Zug wurde gegen eine `DRAFT`-Vorlage versucht |
| 409 | `playthrough_source_not_draft` | Ein Abzweig wurde von einem bereits aktiven Lauf versucht |
| 502 | `story_model_unavailable` | Das Modell hat nicht geantwortet oder unbrauchbare Ausgabe geliefert |
| 500 | `story_configuration_invalid` | Die feste Server-Konfiguration ist ungültig (kein Aufruferfehler) |
| 500 | `story_initialization_inconsistent` / `story_turn_inconsistent` | Die eigene Extraktions-/Validierungskette hat eine intern inkonsistente Antwort erzeugt |

## Swagger UI und OpenAPI

Mit gestarteter API sind die Verträge verfügbar unter:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- ReDoc: `http://localhost:8000/redoc`

## Lokal starten

PostgreSQL und API können gemeinsam gestartet werden:

```bash
./story-starter start
```

`./story-starter` ohne Subcommand bleibt als Alias für `start` erhalten.

Der Root-Launcher unterstützt außerdem:

| Befehl | Zweck |
| --- | --- |
| `start` | Services starten, ohne neu zu bauen |
| `stop` | Container und Compose-Netzwerk entfernen |
| `upgrade` | API-Image neu bauen und Services starten |
| `restart [service ...]` | alle oder ausgewählte Services neu starten |
| `status [service ...]` | Service-Status anzeigen |
| `logs [service ...]` | Logs anzeigen; `-f` verfolgt sie fortlaufend |
| `check` | Compose und API-Health prüfen |
| `clean --yes` | lokales Datenbank-Volume löschen und Schema neu anlegen |

Für die gültigen Services und alle Optionen steht pro Befehl eine eigene
Hilfe zur Verfügung, zum Beispiel `./story-starter logs -h`. `clean` ist
destruktiv und löscht alle lokal gespeicherten Story-Runs; ohne `--yes` wird
eine interaktive Bestätigung verlangt. Eine ausführliche Betriebsanleitung
steht in [`../operations/story-starter.md`](../operations/story-starter.md).

Die API wendet beim Start das PostgreSQL-Basisschema an. Bei einem lokalen
Volume mit dem früheren Schema ist wegen der bewusst fehlenden Datenmigration
zuerst ein manueller Datenbank-Reset erforderlich; Details stehen in
[`persistence.md`](persistence.md).

Der Paketroot ist standardmäßig `prompts` und kann für eine Laufzeitumgebung
über `STORY_GAME_PROMPT_ROOT` gesetzt werden. Die LLM-Konfigurationsdatei ist
standardmäßig `configs/llm.toml` und kann über `STORY_GAME_LLM_CONFIG_PATH`
gesetzt werden.

## Repo-Struktur und Frontend

Das Repo ist in Subprojekte gegliedert: `Backend/` (dieser Python-Code),
`Frontend-Web/` (React/Vite/TypeScript, siehe
[`../../../Frontend-Web/README.md`](../../../Frontend-Web/README.md)), mit
Platz für weitere Subprojekte (z.B. Mobile, Keycloak). `compose.yaml`,
`story-starter` und `.devcontainer/` bleiben am Repo-Root und orchestrieren
über alle Subprojekte hinweg — `story-starter` und lokale
Backend-Entwicklung (`cd Backend && pytest`, `pip install -e .`) sind davon
nicht betroffen.

Für lokale Frontend-Entwicklung gegen eine im Browser laufende App erlaubt
das Backend per CORS standardmäßig `http://localhost:5173` (Vite-Dev-Server);
konfigurierbar über `STORY_GAME_CORS_ALLOWED_ORIGINS` (kommasepariert).
