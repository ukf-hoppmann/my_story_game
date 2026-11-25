# Lokales Keycloak

Keycloak läuft als eigener Compose-Service (`keycloak`) mit einem beim Start
importierten Realm (`configs/keycloak/story-game-realm.json`) — kein
manuelles Einrichten über die Keycloak-Admin-Konsole nötig. Erreichbar ist
es, wie Frontend und Backend auch, über den nginx-Proxy
(`auth.storygame.localhost`).

## Starten

```bash
./story-starter start
```

oder gezielt nur dieser Service:

```bash
docker compose up keycloak
```

Keycloaks Datenbestand (Realm, Nutzer, Sessions) liegt in einer eigenen,
persistenten Postgres-Instanz (Service `keycloak-postgres`, Volume
`story-game-keycloak-db-data`) — analog zur `postgres`-DB der Story-Engine.
Der Realm-Import (`start-dev --import-realm`) läuft zwar bei jedem Start,
überspringt einen bereits existierenden Realm aber und überschreibt ihn
nicht. Das Volume bleibt über `docker compose down` hinweg erhalten und wird
nur bei Bedarf gelöscht (siehe "Zurücksetzen" unten).

Die beiden Test-User (`player-one`/`player-two`, siehe unten) haben in der
Realm-Datei eine fest eingetragene `id` — damit bleibt ihr Keycloak-Nutzer,
und damit der `sub`-Claim in ihren Tokens, über Neustarts und Re-Importe
hinweg stabil. Ohne feste `id` vergibt Keycloak bei jedem Neu-Import eine
neue zufällige UUID, wodurch alle unter der alten Identität gespeicherten
GameRuns für den Nutzer unzugreifbar würden ("Die aufrufende Identität
gehört nicht zu diesem GameRun").

Lokale Änderungen über die Admin-Konsole, die nicht in der Realm-Datei
stehen, werden von einem erneuten Import ohnehin nicht berührt (da der
Import einen existierenden Realm überspringt) — für dauerhafte Anpassungen
trotzdem die Realm-Datei bearbeiten, damit sie auch nach einem
"Zurücksetzen" (siehe unten) wieder vorhanden sind.

### Zurücksetzen

Um Keycloak wirklich wieder aus der Realm-Datei neu aufsetzen zu lassen
(z. B. um eine Änderung an bereits importierten Nutzern zu erzwingen, oder
um einen kaputten lokalen Zustand loszuwerden):

```bash
docker compose down keycloak keycloak-postgres
docker volume rm story-game-keycloak-db-data
docker compose up keycloak
```

Das löscht den kompletten Keycloak-Datenbestand unwiederbringlich (Realm,
Nutzer, Sessions) — nicht die Story-Engine-Datenbank.

- Admin-Konsole: `http://localhost:${KEYCLOAK_HOST_PORT:-8082}` (Login
  `admin`/`admin`, siehe `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD` in
  `compose.yaml`) — direkt über den veröffentlichten Container-Port, nicht
  über nginx.
- Login-/Token-Endpunkte für die Anwendung: `http://auth.storygame.localhost`
  (über nginx, siehe `configs/nginx/storygame.conf`).
- Realm: `story-game`
- Client (für das Frontend): `story-game-frontend`, öffentlicher Client mit
  PKCE, kein Client-Secret

## Test-Logins

Das importierte Realm enthält zwei Spielernutzer, extra für den Fall
"mehrere Spieler parallel" — zwei Browserfenster (oder eines im
Inkognito-Modus), zwei Logins, zwei unabhängige Spielstände, sowie `TestAdmin` mit der Rolle `admin`
(siehe unten):

| Benutzername | Passwort |
| --- | --- |
| `player-one` | `player-one` |
| `player-two` | `player-two` |
| `TestAdmin` | `TestAdmin` (Rolle `admin`) |

## Rolle `admin`

Die Einstellungen der Anwendung (Prompts, Modellwahl, Welt-Tracking) dürfen nur
Nutzer mit der Realm-Rolle `admin` ändern. Das Backend liest die Rolle aus
dem Claim `realm_access.roles` des Access-Tokens und antwortet ohne sie mit
HTTP 403; das Frontend blendet den Menüpunkt nur zusätzlich aus.

- Das importierte Realm enthält die Rolle und den Test-Nutzer `TestAdmin`
  (Passwort `TestAdmin`), der sie trägt. Keycloak speichert Benutzernamen
  kleingeschrieben (`testadmin`); die Anmeldung ignoriert die Schreibweise.
- Ein bereits importiertes Realm wird nicht erneut importiert. Dort die Rolle
  einmalig in der Admin-Konsole anlegen (*Realm roles → Create role*, Name
  `admin`) und dem eigenen Nutzer zuweisen (*Users → Role mapping*), oder das
  Realm wie unter "Zurücksetzen" neu aufsetzen.

## Einen Token manuell holen (ohne Frontend)

Für `curl`-Tests gegen die API direkt, per Password-Grant (nur möglich, weil
der Realm-Export `directAccessGrantsEnabled` für den Client setzt):

```bash
curl -s -X POST \
  "http://auth.storygame.localhost/realms/story-game/protocol/openid-connect/token" \
  -d grant_type=password \
  -d client_id=story-game-frontend \
  -d username=player-one \
  -d password=player-one \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])'
```

Der Token dann als `Authorization: Bearer <token>` an die API:

```bash
curl -H "Authorization: Bearer <token>" http://backend.storygame.localhost/api/v1/runs
```

## Warum Issuer und JWKS-Adresse getrennt konfiguriert sind

Das Backend läuft im `backend`-Container, der Browser läuft auf dem Host.
Ein ausgestellter Token trägt als `iss`-Claim genau die Adresse, über die der
Browser Keycloak erreicht hat (`http://auth.storygame.localhost/...`, via
nginx) — das ist auch die Adresse, gegen die das Backend beim Prüfen
vergleicht (`STORY_GAME_KEYCLOAK_ISSUER`). Um die öffentlichen
Signaturschlüssel zu holen, kann das Backend aber nicht denselben Weg nehmen
(nginx müsste dafür extra durchquert werden, unnötig für einen reinen
Container-zu-Container-Aufruf) — dafür gibt es
`STORY_GAME_KEYCLOAK_JWKS_URI`, das intern über den Compose-Servicenamen
(`http://keycloak:8080/...`) direkt auflöst. Siehe `compose.yaml` und
[HTTP-API](../../development/interfaces/http-api.md).

## Typische Probleme

- **`backend`-Service startet nicht / hängt bei "waiting for keycloak"**: den
  Healthcheck-Status prüfen (`docker compose ps`), Logs mit
  `docker compose logs keycloak` ansehen. Keycloaks Start (inkl. Realm-Import)
  dauert im Dev-Modus einige Sekunden.
- **401 trotz gültigem Login im Frontend**: meist ein Issuer-Mismatch —
  `STORY_GAME_KEYCLOAK_ISSUER` muss exakt der `iss`-Claim im Token sein
  (Groß-/Kleinschreibung, Trailing Slash, Host/Port). Einen Token decodieren
  (z. B. auf jwt.io oder `python3 -c "import jwt;
  print(jwt.decode(token, options={'verify_signature': False}))"`) und mit
  der Backend-Einstellung vergleichen.
- **`auth.storygame.localhost` wird nicht aufgelöst**: die meisten modernen
  Betriebssysteme lösen `*.localhost` automatisch auf `127.0.0.1` auf; falls
  nicht, einen Eintrag in `/etc/hosts` ergänzen (analog zu
  `storygame.localhost`/`backend.storygame.localhost`, falls die dort schon
  funktionieren).
