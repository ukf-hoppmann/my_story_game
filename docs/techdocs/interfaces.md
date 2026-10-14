# Schnittstellen

<!-- Nur öffentliche Schnittstellen: API, CLI, Dateiformate, Hooks, Ereignisse. -->

Ausführliche Anfrage- und Antwortformen, Fehlercodes und Beispiele stehen in
[api.md](../human/technical/api.md); hier steht der Überblick.

## HTTP-API (`/api/v1`)

- Zweck: Spiel-Lebenszyklus, Szenenbilder, Verwaltung von Prompts und Modellwahl.
- Aufruf / Endpunkt: Backend auf `http://backend.storygame.localhost/` (direkt
  `http://localhost:8001`); OpenAPI unter `/docs`.
- Eingabe: JSON; alle IDs sind UUIDs. Authentifizierung per
  `Authorization: Bearer <Keycloak-Token>`, außer `/health` und
  `/api/v1/prompt-profile`.
- Ausgabe: JSON; Spielzustand als `GameDocument` (`game_run`, `game_state`).
- Fehler: 401 ohne gültigen Token, 403 ohne Mitgliedschaft im Lauf
  (`not_a_run_member`) bzw. ohne Rolle `admin` (`forbidden`), 404 bei
  unbekannten oder fremden Objekten, 409 bei Zustandskonflikten, 422 bei
  ungültiger Eingabe.

| Bereich | Endpunkte | Zugriff |
|---|---|---|
| Erreichbarkeit | `GET /health` | öffentlich |
| Promptprofil-Katalog | `GET /api/v1/prompt-profile` | öffentlich |
| Spielläufe | `GET /api/v1/runs`, `GET /api/v1/runs/{run_id}`, `POST /api/v1/runs/proposals`, `POST /api/v1/runs`, `POST /api/v1/runs/{run_id}/playthroughs`, `PATCH /api/v1/runs/{run_id}/configuration`, `POST /api/v1/runs/{run_id}/turns` | angemeldet, Mitglied des Laufs |
| Szenenbilder | `GET /api/v1/scene-images/capabilities`, `POST` und `GET /api/v1/runs/{run_id}/scene-images`, `GET …/{image_id}`, `GET …/{image_id}/content` | angemeldet, Mitglied des Laufs; bei abgeschaltetem Feature 409 `scene_image_disabled` |
| Prompts verwalten | `GET/PUT /api/v1/admin/prompts`, `GET …/history`, `POST …/reset`, `POST/DELETE …/options` | Rolle `admin` |
| Modellwahl verwalten | `GET/PUT /api/v1/admin/models`, `GET …/history`, `POST …/reset` | Rolle `admin` |
| Welt-Tracking schalten | `GET/PUT /api/v1/admin/settings/world-tracking` (`{"enabled": bool}`, Antwort mit `updated_at`, `updated_by`) | Rolle `admin` |
| Welt-Tracking abfragen | `GET /api/v1/settings/world-tracking` (`{"enabled": bool}`) | angemeldet |
| Diagnose | `POST /api/v1/diagnostics/frontend-errors` | angemeldet |

Besonderheiten:

- Ein Zug ist nur in einem `ACTIVE`-Lauf möglich; `DRAFT`-Vorlagen werden
  abgezweigt, nicht bespielt.
- `POST …/scene-images` antwortet sofort mit 202; der Client fragt den Status
  ab (`pending`, `ready`, `failed`). Die Bildbytes brauchen den Bearer-Token.
- Prompt- und Modelländerungen wirken ab dem nächsten Modellaufruf ohne
  Neustart. Neue Optionen lassen sich nur für `genre`, `tone` und
  `prose_style` anlegen. Selbst angelegte Optionen durchlaufen
  aktiv → Papierkorb (archiviert) → endgültig gelöscht; ins Archiv geht nur,
  was keine Spielkonfiguration wählt, und nur dort lässt sich endgültig
  löschen. Mitgelieferte Optionen lassen sich nur zurücksetzen.
- Welt-Tracking ist global und standardmäßig an. Ausgeschaltet läuft beim
  Start und in jedem Zug keine Weltextraktion: Der Vorschlag enthält dann nur
  die im Wizard eingegebenen Figuren, und ein Zug speichert eine leere
  Änderungsmenge. Die Einstellung gilt ab dem nächsten Start oder Zug, auch in
  laufenden Spielen.

## Web-Oberfläche

- Zweck: Spielen, Verwalten der eigenen Geschichten, Administration.
- Aufruf / Endpunkt: `http://storygame.localhost/`

| Route | Inhalt | Zugriff |
|---|---|---|
| `/` | Landing-Page | öffentlich |
| `/library` | Eigene Geschichten | angemeldet |
| `/new` | Wizard für eine neue Geschichte | angemeldet |
| `/stories/:runId` | Spielansicht: Fließtext oder Chat umschaltbar, Szenenbilder pro Zug und Version; Reiter „Welt“ mit Figuren, Orten, Gegenständen, Wesen & Gruppen, Fakten und Wissensmatrix; Hinweis, wenn Welt-Tracking aus ist | angemeldet |
| `/settings` | Tabs Modelle, Aufgaben, Optionen (Genre, Ton & Stil, Spielgefühl, Sonstiges), Direktiven, Spiel: Prompts und Modelle bearbeiten, zurücksetzen, Verlauf; Optionen anlegen, entfernen (Papierkorb, wiederherstellen, endgültig löschen); Welt-Tracking ein- und ausschalten | Rolle `admin` |

Der Kopfbereich zeigt „Anmelden“ oder, angemeldet, ein Menü mit
Benutzername, Geschichten, Neue Geschichte, für Admins Einstellungen, und
„Abmelden“.

## Story-Starter (CLI)

- Zweck: lokalen Docker-Compose-Stack verwalten.
- Aufruf / Endpunkt: `./story-starter <start|stop|down|upgrade|restart|status|logs|check> [Service]`
- Eingabe: optional ein Service (`backend`, `postgres`, `frontend`, `nginx`, `keycloak`).
- Ausgabe: Statusmeldungen und Logs.
- Fehler: Exit-Code ungleich 0 bei fehlgeschlagenem Compose-Aufruf.
- Details: [story-starter.md](../human/operations/story-starter.md)

## Dateiformate

- Prompt-Paket: TOML unter `Backend/prompts/story.base`; nur Quelle für den
  ersten Import, danach gilt die Datenbank.
- Konfiguration: siehe [Konfiguration](configuration.md).
