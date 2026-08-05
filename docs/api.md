# HTTP-API

Die API ist die äußere Schicht des Backends. Sie verwendet die vorhandenen
Anwendungs- und Persistenzports, kennt aber keine PostgreSQL-Tabellen. Ein
LLM kann Prosa und Vorschläge erzeugen; den kanonischen Zustand verändert die
API nur über einen bereits geprüften `ApprovedChangeSet`.

## Endpunkte

| Methode | Pfad | Zweck |
| --- | --- | --- |
| `GET` | `/health` | Erreichbarkeit prüfen |
| `POST` | `/api/v1/runs` | initiale Revision 1 anlegen |
| `GET` | `/api/v1/runs/{run_id}/state` | aktuellen oder historischen Zustand laden |
| `POST` | `/api/v1/runs/{run_id}/commits` | freigegebenen Änderungssatz committen |

Die Commit-Anfrage enthält `proposal_id`, `base_revision` und eine typisierte,
discriminierte Liste von Operationen. Unbekannte Felder und unbekannte
Operationstypen werden am HTTP-Rand abgewiesen. Eine veraltete Revision liefert
HTTP `409`; fachlich ungültige Referenzen liefern HTTP `422`.

## Swagger UI und OpenAPI

Mit gestarteter API sind die interaktiven API-Verträge verfügbar unter:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- ReDoc: `http://localhost:8000/redoc`

## Lokal starten

PostgreSQL und API können gemeinsam gestartet werden:

```bash
./story-starter
```

Das Skript kann direkt aus dem Projektverzeichnis ausgeführt werden. Es baut
das API-Image bei Bedarf, startet PostgreSQL und die API und wartet, bis beide
Dienste bereit sind. Zum Stoppen der Container ohne Löschen des PostgreSQL-
Volumes:

```bash
docker compose down
```

Die API führt beim Start die idempotente PostgreSQL-Migration aus. Für lokale
Tests kann die FastAPI-App mit einem injizierten `JsonGameStateStore` betrieben
werden; dadurch bleiben API-Tests deterministisch und benötigen keinen Dienst.
