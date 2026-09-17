# HTTP-API

Die API deckt den vollständigen Lauf-Lebenszyklus ab: einen Vorschlag
generieren, ihn zu einer Vorlage (`DRAFT`) bestätigen, sie als unabhängiges
aktives Spiel (`ACTIVE`) abzweigen, einen Zug spielen und beides laden oder
auflisten. Die Lauf-Endpunkte verlangen einen gültigen, von Keycloak
signierten Bearer-Token (siehe unten); ohne einen solchen liefern sie HTTP
401. Der reine Promptprofil-Katalog ist dagegen bewusst ohne Token lesbar:
er enthält nur die vom Server auswählbaren Optionen und keine Spiel- oder
Benutzerdaten.

## Endpunkte

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/health` | Erreichbarkeit prüfen |
| `GET` | `/api/v1/prompt-profile` | Paket, Kategorien, Defaults und auswählbare Promptprofil-Optionen lesen (öffentlich) |
| `GET` | `/api/v1/runs` | Eigene `DRAFT`-Vorlagen und `ACTIVE`-Spiele auflisten |
| `GET` | `/api/v1/runs/{run_id}` | Aktuellen oder historischen (`?revision=N`) GameRun/GameState laden |
| `POST` | `/api/v1/runs/proposals` | Vorschlag aus Initialprompt und Modus generieren; persistiert nichts |
| `POST` | `/api/v1/runs` | Einen zuvor generierten Vorschlag zu einer neuen `DRAFT`-Vorlage bestätigen |
| `POST` | `/api/v1/runs/{run_id}/playthroughs` | Eine `DRAFT`-Vorlage als neues unabhängiges `ACTIVE`-Spiel abzweigen |
| `PATCH` | `/api/v1/runs/{run_id}/configuration` | Sprache und editierbare Erzähloptionen als neue Konfigurationsrevision speichern |
| `POST` | `/api/v1/runs/{run_id}/turns` | Einen Zug in einem `ACTIVE`-Spiel spielen |

## Vorschlag, Vorlage und abgespieltes Spiel

Eine neue Vorlage entsteht zweistufig: Vorschlag generieren, dann bestätigen
oder verwerfen. Dazwischen ist noch nichts persistiert.

`POST /api/v1/runs/proposals` erzeugt über `ProposeGameRun` eine vollständige
Eröffnung (Story-Generierung + initiale WorldState-Extraktion) und hält sie
nur transient vor — im Prozessspeicher, 30 Minuten gültig (`InMemoryProposalStore`,
`Backend/src/story_game/infrastructure/persistence/in_memory_proposal_store.py`).
Jede extrahierte Figur ist zunächst eine neutrale Entität; niemand ist
automatisch spielergesteuert. Die Antwort (`RunProposalModel`) enthält eine
`proposal_id`, ein `continuation`-Objekt (`narration` — die eröffnende
Erzählung — plus `options`, 3-4 transiente, unverbindliche
Fortsetzungsvorschläge des Modells, die nirgends persistiert werden), den
vollständigen `WorldState` sowie einen unverbindlichen `suggested_title` und
`suggested_player_entity_ids` (reiner Anzeigehinweis, keine Entscheidung).

`POST /api/v1/runs` bestätigt einen Vorschlag über `ConfirmGameRunProposal`:
der Aufrufer entscheidet je Figur `player`/`npc`/`removed` und je Gegenstand
`removed`, optional mit eigenem `run_name` (sonst greift `suggested_title`).
Erst hier entsteht ein persistenter `GameRun` im Status `DRAFT` mit
Revision 1. Ein Vorschlag kann nur von der Identität bestätigt werden, die
ihn erzeugt hat — ein fremder, unbekannter oder abgelaufener Vorschlag
ergibt in allen drei Fällen identisch HTTP 404 (`error = "not_found"`),
damit die Existenz eines fremden Vorschlags nicht über die Antwort
unterscheidbar ist. Die bestätigte Vorlage bleibt unverändert und kann
beliebig oft erneut abgezweigt werden.

`POST /api/v1/runs/{run_id}/playthroughs` kopiert eine `DRAFT`-Vorlage in
einen neuen, unabhängigen `GameRun` im Status `ACTIVE` (ebenfalls Revision 1,
eigene `run_id`). Nur `DRAFT`-Läufe können abgezweigt werden; der Versuch,
einen bereits aktiven Lauf erneut abzuzweigen, ergibt HTTP 409
(`error = "playthrough_source_not_draft"`). Die aufrufende Identität muss
bereits Mitglied der Quell-Vorlage sein, sonst HTTP 403
(`error = "not_a_run_member"`) — dieselbe Prüfung wie beim Laden.

`POST /api/v1/runs/{run_id}/turns` spielt einen Zug ausschließlich in einem
`ACTIVE`-Lauf. Gegen eine `DRAFT`-Vorlage ergibt das HTTP 409
(`error = "run_not_active"`).

## Anfrage- und Antwortformen

`POST /api/v1/runs/proposals` verlangt `initial_prompt`, `control_mode`
(`"player"` oder `"director"`) und eine Liste `controllable_characters`
steuerbarer Figuren (`name`, optional `description`). Im Player Mode muss die
Liste genau ein Element enthalten; im Director Mode darf sie null oder
mehrere Elemente enthalten. Zusätzlich kann der Client `language` sowie ein
vollständiges `prompt_profile` übergeben. Lässt er eines dieser Felder weg,
verwendet die API die bisherigen serverseitigen Defaults aus
`api/default_configuration.py`, damit bestehende Clients unverändert
funktionieren. Kein `run_name` an dieser Stelle — der wird erst beim
Bestätigen gebraucht.

`POST /api/v1/runs` verlangt `proposal_id` (aus der vorherigen
`/proposals`-Antwort), optional `run_name`, sowie `character_decisions`
(je Eintrag `entity_id`, `role: "player"|"npc"`, optional `removed`) und
`item_decisions` (je Eintrag `entity_id`, optional `removed`) — damit
entscheidet der Aufrufer erst hier, welche vorgeschlagene Figur er selbst
steuert.

`POST /api/v1/runs/{run_id}/turns` verlangt nur `player_input` und liefert
`TurnResultModel`: den vollständigen aktualisierten `GameStateModel`, dasselbe
`continuation`-Objekt (`narration` — identisch mit der Prosa des zuletzt
gespielten Zugs — plus `options`, transient und nicht persistiert, siehe
oben) sowie `proposed_change_count`, `summary_failed` und optional
`summary_failure_message` als transiente Diagnose — ein Fehlschlag der
Zusammenfassung lässt den Zug selbst unangetastet (siehe TASK-023).

## Promptprofil auswählen und nachträglich ändern

`GET /api/v1/prompt-profile` liefert den vom Server verwendeten Promptkatalog
`story.base`/`1`: Paket-ID und -version sowie alle Kategorien mit Options-ID,
Beschreibung und Default. Der Katalog enthält auch `control_mode` und
`extraction`, damit ein Client seine Auswahloberfläche vollständig aufbauen
kann. Sie sind aber keine editierbaren Felder des Promptprofils:
`control_mode` wird beim Erstellen eines Vorschlags separat übergeben,
`extraction` gehört nicht in die gespeicherte Spielkonfiguration. Der
Endpunkt ist aktuell öffentlich und liefert keine nutzerbezogenen Daten.

Das beim Vorschlag optional übergebene `prompt_profile` enthält genau die
editierbaren Story-Kategorien `genre`, `tone`, `prose_style`, `perspective`,
`pacing`, `length`, `player_agency`, `consequence`, `challenge` und
`content_profile`. Die API validiert alle Options-IDs gegen das referenzierte
Promptpaket, bevor sie den Modellworkflow startet. Erzählerische Grenzen,
Paket-ID und -version bleiben serverbestimmt; `control_mode` wird nur beim
Erstellen festgelegt, weil er die Mitgliedschafts- und Figurenregeln prägt.

`PATCH /api/v1/runs/{run_id}/configuration` ersetzt die vollständige
editierbare Auswahl eines bestehenden Runs. Der Request enthält
`base_revision`, `language` und das vollständige editierbare `prompt_profile`
(kein partieller Patch). Die API prüft Mitgliedschaft und erwartete Revision,
validiert die Auswahl erneut und liefert den neuen `GameState` mit seiner
Konfigurationsrevision zurück. Sie übernimmt dabei die vorhandenen
`control_mode`, `narrative_boundaries`, `prompt_package_id` und
`prompt_package_version` unverändert; diese Werte können über diesen
Endpunkt nicht verändert werden.

`GET /api/v1/runs` liefert `RunSummaryModel`-Einträge (`id`, `name`,
`status`, `current_revision`, `game_role`, `updated_at`) ohne vollen
WorldState, damit eine Liste nicht pro Zeile einen kompletten Weltsnapshot
lädt. `GET /api/v1/runs/{run_id}` liefert weiterhin das vollständige
`GameDocument` (siehe unten) — nur, wenn die aufrufende Identität Mitglied
dieses Runs ist, sonst HTTP 403 (`error = "not_a_run_member"`).

Das gemeinsame Transportdokument für Confirm-, Playthrough- und
Load-Antworten heißt `GameDocument` und enthält sowohl `game_run` als auch
`game_state`. Der
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

## Authentifizierung

Alle Lauf-Endpunkte unter `/api/v1/runs` müssen einen
`Authorization: Bearer <token>`-Header mit einem gültigen, von Keycloak
signierten Access-Token mitschicken. `get_current_initiator`
(`api/dependencies.py`) prüft diesen Token über `KeycloakTokenVerifier`
(`api/auth/token_verifier.py`) gegen die JWKS (öffentliche Signaturschlüssel)
des konfigurierten Realms und leitet daraus `issuer` (die Realm-URL) und
`subject` (der Token-`sub`-Claim) als aufrufende Identität ab. Fehlt der
Header, ist er falsch formatiert, oder ist der Token ungültig/abgelaufen/vom
falschen Realm, antwortet die API mit HTTP 401 — bevor irgendein
Anwendungsfall ausgeführt wird.

Relevante Einstellungen (`ApiSettings`, Umgebungsvariablen):

- `STORY_GAME_KEYCLOAK_ISSUER` — die vertraute Realm-URL, z. B.
  `http://auth.storygame.localhost/realms/story-game`; von dort werden auch
  standardmäßig die JWKS bezogen
  (`<issuer>/protocol/openid-connect/certs`).
- `STORY_GAME_KEYCLOAK_AUDIENCE` — erwarteter `aud`-Claim (Client-ID); leer
  lassen, um die Audience-Prüfung zu deaktivieren.
- `STORY_GAME_KEYCLOAK_JWKS_URI` — überschreibt, woher die öffentlichen
  Schlüssel geholt werden, falls das nicht derselbe Weg wie der Issuer ist
  (im Docker-Setup der Fall, siehe `compose.yaml` und
  `docs/human/operations/keycloak.md`).

Details zum lokalen Keycloak-Setup (Docker, Realm-Import, Test-Login) stehen
in [`../operations/keycloak.md`](../operations/keycloak.md).

Die eigentliche Autorisierung — welche Identität einen konkreten Run sehen,
bespielen oder abzweigen darf — passiert unabhängig davon in der
Anwendungslogik: `LoadGame` (genutzt von `GET /api/v1/runs/{run_id}`,
`POST /.../turns` und `POST /.../playthroughs`) prüft die Mitgliedschaft in
`GameRun.members` und liefert sonst `not_a_run_member`. `GET /api/v1/runs`
filtert direkt nach `(issuer, subject)`.

## Fehlerantworten

Jede Fehlerantwort hat die Form `{"error": <code>, "detail": <Text>, ...}`.
Über die bereits dokumentierten Zustandsfehler hinaus (`not_found`,
`revision_conflict`, `domain_validation_failed`, `invalid_prompt_selection`,
`persistence_unavailable`, …) kennt die Lauf-API zusätzlich:

| HTTP | `error` | Bedeutung |
| --- | --- | --- |
| 401 | `unauthorized` | Kein, ein falsch formatierter, oder ein ungültiger/abgelaufener Bearer-Token |
| 403 | `not_a_run_member` | Die aufrufende Identität gehört nicht zum GameRun |
| 409 | `run_not_active` | Ein Zug wurde gegen eine `DRAFT`-Vorlage versucht |
| 409 | `playthrough_source_not_draft` | Ein Abzweig wurde von einem bereits aktiven Lauf versucht |
| 502 | `story_model_unavailable` | Das Modell hat nicht geantwortet oder unbrauchbare Ausgabe geliefert |
| 500 | `story_configuration_invalid` | Die serverseitig validierte Spielkonfiguration ist ungültig (kein Aufruferfehler) |
| 500 | `story_initialization_inconsistent` / `story_turn_inconsistent` | Die eigene Extraktions-/Validierungskette hat eine intern inkonsistente Antwort erzeugt |

## Swagger UI und OpenAPI

Mit gestarteter API sind die Verträge direkt unter folgenden Adressen
verfügbar; über den lokalen Compose-Proxy sind sie außerdem unter
`http://backend.storygame.localhost/…` erreichbar:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- ReDoc: `http://localhost:8000/redoc`

## Lokal starten

Der vollständige lokale Stack — PostgreSQL, Backend, Frontend, nginx und
Keycloak — kann gemeinsam gestartet werden:

```bash
./story-starter start
```

`./story-starter` ohne Subcommand bleibt als Alias für `start` erhalten.

Der Root-Launcher unterstützt außerdem:

| Befehl | Zweck |
| --- | --- |
| `start` | Services starten, ohne neu zu bauen |
| `stop` | Container und Compose-Netzwerk entfernen |
| `down` | Container, Compose-Netzwerk, Volumes und verwaiste Container entfernen (destruktiv) |
| `upgrade` | API-Image neu bauen, alle Container neu erzeugen und starten |
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

Für die Compose-App erlaubt das Backend per CORS
`http://storygame.localhost`; für einen separat gestarteten Vite-Dev-Server
kann `STORY_GAME_CORS_ALLOWED_ORIGINS` entsprechend gesetzt werden
(kommasepariert).
