# Lokaler Story-Starter

[`story-starter`](../../../story-starter) ist ein Python-CLI für die lokale
Docker-Compose-Umgebung. Es startet und verwaltet PostgreSQL und die API. Das
Frontend wird weiterhin separat mit Vite gestartet.

Der Aufruf ohne Subcommand bleibt aus Kompatibilitätsgründen ein Alias für
`start`.

## Befehle

```bash
./story-starter start
./story-starter stop
./story-starter upgrade
./story-starter restart
./story-starter status
./story-starter logs
./story-starter check
```

`start` startet die Services ohne Image-Neubau. `upgrade` baut das API-Image
neu und startet anschließend die Umgebung. `stop` entfernt die Container und
das Compose-Netzwerk, lässt das persistente Datenbank-Volume aber bestehen.

`restart` startet standardmäßig alle Services neu. Einzelne Services können
explizit angegeben werden:

```bash
./story-starter restart api
./story-starter restart postgres
```

Für `restart`, `status` und `logs` sind `all`, `api` und `postgres` gültige
Servicewerte. Die vollständige, jeweils passende Hilfe ist direkt verfügbar:

```bash
./story-starter logs -h
./story-starter restart -h
```

Logs können fortlaufend verfolgt werden:

```bash
./story-starter logs api --follow
./story-starter logs postgres --tail 100
```

`check` validiert die Compose-Datei, zeigt laufende Services und prüft den
HTTP-Endpunkt `http://localhost:${API_HOST_PORT:-8000}/health`.

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
insbesondere `API_HOST_PORT` und `POSTGRES_HOST_PORT`.
