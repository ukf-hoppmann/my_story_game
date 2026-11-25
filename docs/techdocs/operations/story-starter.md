# Lokaler Story-Starter

[`story-starter`](../../../story-starter) ist ein Python-CLI für die lokale
Docker-Compose-Umgebung. Es startet und verwaltet den vollständigen lokalen
Stack: PostgreSQL, Backend, Frontend, nginx und Keycloak. Die Browser-App ist
über `http://storygame.localhost/` erreichbar; das Backend steht hinter dem
Proxy unter `http://backend.storygame.localhost/`.

Der Aufruf ohne Subcommand bleibt aus Kompatibilitätsgründen ein Alias für
`start`.

## Befehle

```bash
./story-starter start
./story-starter stop
./story-starter down
./story-starter upgrade
./story-starter restart
./story-starter status
./story-starter logs
./story-starter check
./story-starter clean
```

`start` startet alle Services ohne Image-Neubau. `upgrade` baut das Backend-
Image neu und erzeugt alle Container neu (`--force-recreate`), bevor die Umgebung
startet — wichtig für `frontend`, das kein eigenes Image baut, sondern
`npm install` bei jedem Container-Start gegen den eingebundenen Quellcode
ausführt: ohne Neuerzeugung würde eine geänderte `package.json` (z. B. eine
neue Abhängigkeit) im laufenden Container sonst nicht nachgezogen. `stop`
entfernt die Container und das Compose-Netzwerk, lässt das persistente
Datenbank-Volume aber bestehen. `down` ist das vollständige Cleanup: Es
entfernt zusätzlich Volumes und verwaiste Container und löscht damit die
lokalen Daten ohne interaktive Rückfrage.

`restart`, `status` und `logs` verwenden ohne Serviceangabe den ganzen Stack.
Einzelne Services können explizit angegeben werden: `backend`, `postgres`,
`frontend`, `nginx` oder `keycloak`.

```bash
./story-starter restart backend
./story-starter restart postgres
```

`all` steht ebenfalls für den vollständigen Stack. Die vollständige, jeweils
passende Hilfe ist direkt verfügbar:

```bash
./story-starter logs -h
./story-starter restart -h
```

Logs können fortlaufend verfolgt werden:

```bash
./story-starter logs backend --follow
./story-starter logs postgres --tail 100
```

`check` validiert die Compose-Datei, zeigt laufende Services und prüft den
direkt veröffentlichten Backend-Endpunkt
`http://localhost:${BACKEND_HOST_PORT}/health` (Standard `8001` aus
`configs/docker/docker.env`). Der Browser sollte
stattdessen die Proxy-Adressen unter `*.storygame.localhost` verwenden.

## Datenbank zurücksetzen

`clean` löscht das lokale PostgreSQL-Volume und startet anschließend eine
leere Datenbank. Die API wendet beim Start das Basisschema automatisch an.
Alle lokal gespeicherten Story-Runs gehen dabei verloren:

```bash
./story-starter clean
./story-starter clean --yes
```

Ohne `--yes` verlangt der Befehl eine interaktive Bestätigung. `--yes` ist für
Skripte und nicht-interaktive Aufrufe vorgesehen und sollte nur bewusst
verwendet werden.

## Globale Optionen

Globale Optionen werden vor dem Subcommand angegeben:

```bash
./story-starter --compose-file compose.yaml status
./story-starter --project-name story-game-dev status
```

Die Host-Ports bleiben über die Compose-Umgebungsvariablen konfigurierbar,
insbesondere `BACKEND_HOST_PORT`, `POSTGRES_HOST_PORT`, `FRONTEND_HOST_PORT`,
`KEYCLOAK_HOST_PORT` und `PROXY_HOST_PORT`. Ohne `--env-file` verwendet der
Launcher die projektweite Standarddatei `configs/docker/docker.env`.
