# Betrieb

<!-- Nur der aktuelle Stand. Anleitungen je Thema stehen unter operations/. -->

Dokumentiert ist der lokale Betrieb mit Docker Compose. Ein weiterer
Bereitstellungsweg ist nicht eingerichtet.

## Deployment

Der Stack besteht aus sechs Compose-Services (`compose.yaml`):

| Service | Aufgabe |
|---|---|
| `postgres` | Datenbank der Anwendung, Volume `story-game-postgres-data` |
| `keycloak-postgres` | Datenbank von Keycloak, Volume `story-game-keycloak-db-data` |
| `keycloak` | Anmeldung (OIDC); importiert den Realm `story-game` aus `configs/keycloak` |
| `backend` | FastAPI-Anwendung; wendet beim Start die Migrationen an (`STORY_GAME_AUTO_MIGRATE`) |
| `frontend` | Vite-Entwicklungsserver; führt bei jedem Containerstart `npm install` aus |
| `nginx` | Proxy für `storygame.localhost`, `backend.storygame.localhost` und `auth.storygame.localhost` |

Voraussetzungen und Geheimnisse (`llm.secrets.toml`, `scene_image.secrets.toml`)
stehen in der [README](../../README.md), alle Einstellungen in der
[Konfiguration](configuration.md). Das Backend-Image wird mit
`./story-starter upgrade` neu gebaut; Frontend-Änderungen brauchen kein Image.
Die Datenbank ändert sich nur über die Migrationen unter
`Backend/src/story_game/infrastructure/persistence/postgres/migrations`.

Der Modellanbieter läuft außerhalb des Stacks: LM Studio auf dem Host
(`host.docker.internal:1234`), Groq und Gemini über das Internet, Modal für
Szenenbilder.

## Running

| Aufgabe | Befehl oder Ort | Anleitung |
|---|---|---|
| Stack starten, stoppen, neu erzeugen, Status, Logs | `./story-starter start`, `stop`, `down`, `upgrade`, `restart`, `status`, `logs` | [Story-Starter](operations/story-starter.md) |
| Erreichbarkeit prüfen | `./story-starter check`, `GET /health` am Backend | [Story-Starter](operations/story-starter.md) |
| Lokale Daten zurücksetzen | `./story-starter clean` | [Story-Starter](operations/story-starter.md) |
| Anmelden, Test-Logins, Rolle `admin` | Keycloak unter `http://auth.storygame.localhost/` | [Keycloak](operations/keycloak.md) |
| Logs lesen, Profil `prod` oder `debug` | `Backend/logs/story-game.log`, `STORY_GAME_LOG_MODE` | [Logging](operations/logging.md) |
| Modellanbieter einrichten | `llm.toml`, `llm.secrets.toml`, Modellwahl in `/settings` | [LM Studio](operations/lmstudio.md), [Groq](operations/groq.md), [Gemini](operations/gemini.md) |
| Szenenbilder ein- oder ausschalten | `[scene_image]` in `app.toml` | [Szenenbilder](operations/szenenbilder.md) |
| Welt-Tracking ein- oder ausschalten | Tab „Spiel“ in `/settings` (Rolle `admin`) | [Konfiguration](configuration.md) |

Die Anwendung ist unter `http://storygame.localhost/` erreichbar. Der Browser
nutzt die Proxy-Adressen, nicht die direkt veröffentlichten Host-Ports.

## Failure modes

| Symptom | Cause | Resolution |
|---|---|---|
| `backend` startet nicht und wartet auf Keycloak | Keycloak ist noch nicht gesund; der Realm-Import braucht einige Sekunden | `docker compose ps` und `docker compose logs keycloak` prüfen ([Keycloak](operations/keycloak.md)) |
| 401 trotz Login im Frontend | `STORY_GAME_KEYCLOAK_ISSUER` entspricht nicht dem `iss` des Tokens | Token dekodieren und Einstellung angleichen ([Keycloak](operations/keycloak.md)) |
| 403 `forbidden` auf `/settings` oder `/api/v1/admin/*` | Der Nutzer hat die Realm-Rolle `admin` nicht | Rolle zuweisen; in einem bereits importierten Realm einmalig von Hand ([Keycloak](operations/keycloak.md)) |
| `auth.storygame.localhost` wird nicht aufgelöst | `*.localhost` löst nicht auf `127.0.0.1` auf | Eintrag in `/etc/hosts` ergänzen |
| 502 `story_model_unavailable` beim Start oder Zug | Das Modell ist nicht erreichbar, hat das Zeitlimit überschritten, liefert Ungültiges oder begrenzt die Rate | Anbieter und Modellwahl prüfen; bei Rate-Limits Aufrufe strecken; LM Studio aus dem Container über `host.docker.internal` ansprechen |
| 422 `domain_validation_failed` bei Start oder Zug | Die Extraktion hat Änderungen vorgeschlagen, die die Invarianten des Spielzustands verletzen (z. B. eine Ortsverknüpfung, die nicht auf einen Ort zeigt) | Aktion wiederholen; der Zug wird verworfen, der Spielstand bleibt unverändert. Bei schwachen lokalen Modellen Welt-Tracking ausschalten |
| 409 `scene_image_disabled` | Szenenbilder sind abgeschaltet | `enabled = true` in `[scene_image]` setzen und neu starten ([Szenenbilder](operations/szenenbilder.md)) |
| Szenenbild bleibt `pending` oder wird `failed` | Der Server endete mitten in der Erzeugung, oder LLM, Modal oder Token schlugen fehl | Nach `2 × timeout_seconds + 120 s` gilt das Bild als verwaist; neu anstoßen ([Szenenbilder](operations/szenenbilder.md)) |
| Frontend zeigt nach `npm`-Änderungen alte Abhängigkeiten | Der Container wurde nicht neu erzeugt | `./story-starter upgrade` |
