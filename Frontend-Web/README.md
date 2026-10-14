# Frontend-Web

Web-Frontend des Story-Spiels: React 19 + Redux Toolkit (inkl. RTK Query) +
React Router + TypeScript, gebaut mit Vite.

Dies ist der Neuaufbau, der das ursprüngliche MVP-Frontend abgelöst hat (das
alte Frontend liegt zur Referenz unter `../Frontend-Web-old`, siehe dessen
README).

## Stack

- React 19 + Vite + TypeScript
- Redux Toolkit + react-redux + RTK Query für State-Management/API-Anbindung
- React Router für Routing (inkl. routenbasiertem Auth-Gate, siehe unten)
- Keycloak (`keycloak-js`) für Login
- Vitest + React Testing Library für Tests

## Entwicklung

```bash
npm install
npm run dev      # Dev-Server
npm run build    # Typecheck + Build
npm run test     # Vitest
npm run lint     # oxlint
```

`.env.development` setzt `VITE_API_BASE_URL` (Backend-Basis-URL). Keycloak-
Variablen (`VITE_KEYCLOAK_URL`/`VITE_KEYCLOAK_REALM`/`VITE_KEYCLOAK_CLIENT_ID`)
haben sinnvolle Defaults für die lokale Docker-Compose-Umgebung (siehe
`src/api/auth.ts`).

Läuft im Docker-Compose-Stack (`../compose.yaml`, Service `frontend`) hinter
nginx unter `storygame.localhost`.

## Struktur

- `src/api/` — typisierter Fetch-Client (`client.ts`), Domain-Typen
  (`types.ts`), Keycloak-Anbindung (`auth.ts`), RTK-Query-Slice
  (`apiSlice.ts`).
- `src/app/` — Redux-Store, typisierte Hooks, `RequireAuth`-Routen-Gate.
- `src/components/` — geteilte UI-Bausteine (Button, Chip, Panel, ImageSlot,
  Paragraphs).
- `src/features/wizard/` — Redux-Slice für den mehrstufigen
  Story-Erstellungs-Assistenten.
- `src/routes/` — die Screens (Landing, Library, Wizard, Play) plus die
  Routentabelle.
- `src/styles/tokens.css` — Design-Tokens (Bordeaux/Pergament-Theme).

Zusätzliche gemeinsam genutzte Bausteine sind `AppHeader` und `ErrorBanner`.

## Auth

`/` (Landing) ist ohne Login erreichbar. Alle anderen Routen sind über die
`RequireAuth`-Layout-Route geschützt, die den Keycloak-Login-Redirect erst
beim Betreten einer geschützten Route auslöst (nicht beim App-Start).

Der Wizard arbeitet mit einem Review-Schritt und bestätigt einen transienten
Vorschlag erst nach der Rollenentscheidung für Figuren. Die Play-Ansicht
zeigt nach regulären Zügen die vom Backend gelieferten
Fortsetzungsoptionen als zweistufige Chips: erster Klick übernimmt den Text,
zweiter Klick sendet ihn ab; die freie Eingabe bleibt erhalten. Optionen aus
der Eröffnung werden aktuell noch nicht im Play-Screen angezeigt, weil sie
`GameDocument` nicht enthält. Geschichte und Chronik zeigen den Story-Feed
beziehungsweise die geordnete Summary-Segmentkette.

Der Reiter „Welt“ ersetzt Bühne und Seitenleiste durch eine Ansicht des
gesamten `WorldState` aus dem bereits geladenen `GameDocument` (kein eigener
Endpunkt). Themen-Tabs trennen Figuren, Orte, Gegenstände, Wesen & Gruppen,
Fakten (mit Weltregeln) und eine Wissensmatrix. In den Eintrags-Tabs steht
links eine Liste mit ein bis zwei Hauptmerkmalen, rechts die Detailansicht mit
Zuständen, Beziehungen (anklickbar), dem Wissen der Figur und den Fakten über
den Eintrag. Angezeigt wird alles, auch vergessenes Wissen und jede
Sichtbarkeit; gefiltert wird nicht. Ein Zug-Regler zeigt den Wissensstand zu
einem früheren Zug und erscheint nur, wenn Wissenseinträge existieren. Die
Ableitungen liegen testbar in `src/routes/Play/World/worldModel.ts`.

Im Wizard kann der Ton ausdrücklich leer bleiben (`Kein zusätzlicher Ton`). In
diesem Fall wird keine zusätzliche Tonvorgabe an das Modell gesendet; die
Stimmung des gewählten Genres bleibt maßgeblich.

Frontend-Fehler werden zentral klassifiziert: 401 führt zum Re-Login, echte
Backend-Fehler zeigen den Backend-Text, und sonstige Tooling-Fehler werden
fire-and-forget für Diagnosezwecke gemeldet.

## Design

Bordeaux/Pergament-Theme als Default (`dark_fantasy`-Genre), als CSS-Tokens
angelegt, damit ein späteres zweites Genre-Theme ohne Strukturumbau möglich
ist — aktuell ist aber nur dieses eine Theme ausimplementiert. Genre/Ton und
alle weiteren Story-Optionen im Wizard kommen live vom Backend
(`GET /api/v1/prompt-profile`), nicht hartkodiert.
