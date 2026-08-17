# HTTP-API

Die aktuelle API ist eine bewusst kleine Testgrenze für den vollständigen
Spielzustand. Sie ist noch keine fertige Spielzug-, LLM- oder
Konfigurations-API.

## Endpunkte

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/health` | Erreichbarkeit prüfen |
| `POST` | `/api/v1/runs` | vollständigen neuen GameRun mit Revision 1 speichern |
| `GET` | `/api/v1/runs/{run_id}/state` | vollständigen aktuellen GameRun und GameState laden |
| `GET` | `/api/v1/runs/{run_id}/state?revision=N` | einen historischen GameState laden |

Das gemeinsame Transportdokument heißt `GameDocument` und enthält sowohl
`game_run` als auch `game_state`. Der GameState enthält die komplette
`GameConfiguration`, den `WorldState` einschließlich Goals und den
`StoryState`. Fremde Felder und fachlich inkonsistente IDs werden abgewiesen.

`world.scene_location_ids` ist eine geordnete Liste von Orts-UUIDs und benennt,
wo die Erzählung spielt; der erste Eintrag ist der Hauptschauplatz. Die Liste
ist getrennt von den `located_in`-Beziehungen: diese sagen, wo eine Entität ist,
jene, wohin die Erzählung blickt. IDs, die keinen vorhandenen Ort bezeichnen,
sowie Duplikate werden abgewiesen.

`schema_version` kennzeichnet den Aufbau des Transportdokuments und steigt nur
bei brechenden Änderungen: entfernten oder umbenannten Feldern, geänderten Typen
oder geänderter Bedeutung eines Feldes. Ein zusätzliches Feld mit Standardwert
ist dagegen rein additiv — ältere Clients ignorieren es, und ältere Dokumente
bleiben ohne Anpassung gültig. `scene_location_ids` ist ein solcher Fall; die
Version bleibt deshalb bewusst `1`.

Alle internen IDs werden im OpenAPI-Schema als `string` mit `format: uuid`
ausgewiesen und im JSON in kanonischer UUID-Schreibweise übertragen. Das gilt
auch für `run_id` im Pfad; eine nicht als UUID parsebare ID führt zu HTTP 422.
`game_run.name` ist der lesbare Anzeigename und unabhängig von der technischen
ID. Keycloak-, Prompt-Paket- und Promptprofil-Kennungen bleiben Text.

`GameConfiguration.prompt_profile` ist ein vollständiges Objekt mit zehn
Pflichtfeldern. Die API ergänzt keine Paketdefaults. Vor dem Speichern prüft
die Application jede Options-ID gegen `prompt_package_id` und
`prompt_package_version`. Eine unbekannte Auswahl ergibt HTTP 422 mit
`error = "invalid_prompt_selection"`, `category`, `option_id` und einer
lesbaren Beschreibung, damit eine UI genau dieses Feld erneut abfragen kann.

Der POST-Endpunkt legt absichtlich nur einen neuen Lauf in Revision 1 an.
Konfigurationsrevisionen und atomare StoryTurn-Commits sind bereits als
Application- und Persistenzoperationen vorhanden, werden aber noch nicht als
Produktendpunkte veröffentlicht. Es gibt insbesondere keinen direkten
HTTP-Endpunkt, über den ein LLM Zustandsänderungen schreiben kann.

## Swagger UI und OpenAPI

Mit gestarteter API sind die Verträge verfügbar unter:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- ReDoc: `http://localhost:8000/redoc`

## Lokal starten

PostgreSQL und API können gemeinsam gestartet werden:

```bash
./story-starter
```

Die API wendet beim Start das PostgreSQL-Basisschema an. Bei einem lokalen
Volume mit dem früheren Schema ist wegen der bewusst fehlenden Datenmigration
zuerst ein manueller Datenbank-Reset erforderlich; Details stehen in
[`persistence.md`](persistence.md).

Der Paketroot ist standardmäßig `prompts` und kann für eine Laufzeitumgebung
über `STORY_GAME_PROMPT_ROOT` gesetzt werden.
