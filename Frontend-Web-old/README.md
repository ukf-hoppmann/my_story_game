# Frontend-Web-old

> **Abgelöst.** Dieses Verzeichnis ist das ursprüngliche MVP-Frontend, nicht
> mehr im Compose-Stack eingebunden und wird nicht weiterentwickelt. Der
> aktive Nachfolger liegt unter [`../Frontend-Web`](../Frontend-Web/README.md).
> Diese README bleibt als historische Referenz erhalten.

React + Vite + TypeScript. Die App spricht gegen die `Backend`-API unter
`/api/v1/runs` und meldet Benutzer vor dem Rendern über Keycloak an (siehe
[`../docs/human/technical/api.md`](../docs/human/technical/api.md)).

## Lokal starten

Den vollständigen lokalen Stack aus dem Repo-Root starten:

```bash
./story-starter start
```

Die Browser-App läuft dann über nginx unter `http://storygame.localhost/`.
Frontend, Backend und Keycloak sind dort bereits verbunden.

Für eine separate Vite-Entwicklung in diesem Verzeichnis:

```bash
npm install
npm run dev
```

Vite läuft unter `http://localhost:5173`. Die versionierte
`.env.development` verweist auf die vom Compose-Proxy bereitgestellten
Adressen `http://backend.storygame.localhost` und
`http://auth.storygame.localhost`. Bei abweichenden lokalen Adressen müssen
`VITE_API_BASE_URL`, `VITE_KEYCLOAK_URL`, Realm und Client-ID passend
überschrieben werden. Der Backend-CORS-Origin ist über
`STORY_GAME_CORS_ALLOWED_ORIGINS` konfigurierbar.

## Anmeldung

`src/api/auth.ts` initialisiert `keycloak-js` mit `login-required`, setzt den
Bearer-Token am gemeinsamen API-Client und erneuert ihn bei Ablauf. Der
lokale Realm enthält die Testnutzer und den Frontend-Client; Login- und
Troubleshooting-Hinweise stehen in
[`../docs/human/operations/keycloak.md`](../docs/human/operations/keycloak.md).

## Struktur

```
src/
  api/
    client.ts        Fetch-Wrapper, Fehler-Envelope-Mapping, Auth-Injection-Point
    auth.ts          Keycloak-Login, Token-Erneuerung und Logout
    types.ts          Handgeschriebene Typen passend zu den Backend-Schemas
    useApiRequest.ts   Kleiner Hook für Lade-/Erfolg-/Fehlerzustände
  screens/
    RunsListScreen.tsx     Eigene Vorlagen (DRAFT) und aktive Spiele (ACTIVE)
    StartDraftScreen.tsx    Neue Vorlage erzeugen + sofort als Spiel abzweigen
    PlayScreen.tsx           Laden, ggf. Spiel starten, Züge spielen
```

Kein Router (nur drei Screens, linearer Fluss), kein OpenAPI-Codegen
(Typen von Hand gepflegt) — Begründung siehe Projektplan. Das Frontend besitzt
weiterhin kein eigenes Dockerfile; der Compose-Service nutzt das Node-Image
und führt `npm install` gegen den eingebundenen Quellcode aus.

## Bekannte Lücken (MVP)

- Kein visuelles Design (nur funktionale Basis-Styles in `src/index.css`).
- Kein Turn-Historie-Scroll-/Paginierungsverhalten für lange Läufe.
- Kein Umgang mit `PAUSED`/`COMPLETED`-Status (Backend setzt diese nie).
- Die Oberfläche verwendet beim Erstellen noch die serverseitigen
  Promptprofil-Defaults. Der API-Katalog und die Konfigurationsänderung sind
  verfügbar, aber noch nicht als Auswahloberfläche umgesetzt.
