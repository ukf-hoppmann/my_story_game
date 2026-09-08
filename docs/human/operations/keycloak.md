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

Der Realm-Import läuft bei jedem Start erneut (`start-dev --import-realm`);
lokale Änderungen über die Admin-Konsole, die nicht in der Realm-Datei
stehen, gehen beim nächsten Neustart verloren — für dauerhafte Anpassungen
die Realm-Datei bearbeiten.

- Admin-Konsole: `http://localhost:${KEYCLOAK_HOST_PORT:-8081}` (Login
  `admin`/`admin`, siehe `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD` in
  `compose.yaml`) — direkt über den veröffentlichten Container-Port, nicht
  über nginx.
- Login-/Token-Endpunkte für die Anwendung: `http://auth.storygame.localhost`
  (über nginx, siehe `configs/nginx/storygame.conf`).
- Realm: `story-game`
- Client (für das Frontend): `story-game-frontend`, öffentlicher Client mit
  PKCE, kein Client-Secret

## Test-Logins

Das importierte Realm enthält zwei Beispielnutzer, extra für den Fall
"mehrere Spieler parallel" — zwei Browserfenster (oder eines im
Inkognito-Modus), zwei Logins, zwei unabhängige Spielstände:

| Benutzername | Passwort |
| --- | --- |
| `player-one` | `player-one` |
| `player-two` | `player-two` |

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
`docs/human/technical/api.md`.

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
