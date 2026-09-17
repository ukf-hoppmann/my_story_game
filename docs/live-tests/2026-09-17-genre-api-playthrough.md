# Live-Test: Genre-Annahme über die API

## Ergebnis

Am 17. September 2026 wurde der Lauf-Lebenszyklus der lokalen Story-Game-API
mit dem Keycloak-Testkonto `player-one` geprüft. Für jedes verfügbare Genre
wurde ein eigener Lauf angelegt. Ziel waren drei reguläre Züge pro Genre.

| Genre | Vorschlag | Vorlage/Playthrough | Zug 1 | Zug 2 | Zug 3 | Befund |
|---|---:|---:|---:|---:|---:|---|
| `dark_fantasy` | 201 | 201 / 201 | 201 | 201 | 201 | vollständig erfolgreich |
| `fantasy` | 201 | 201 / 201 | 502 | 502 | 502 | Provider-Limit bei jedem Zug |
| `science_fiction` | 502 | – | – | – | – | Provider-Limit schon bei Initialisierung |
| `mystery` | 502 | – | – | – | – | Provider-Limit schon bei Initialisierung |
| `steam_punk` | 502 | – | – | – | – | Provider-Limit schon bei Initialisierung |

Die HTTP-502-Antworten enthielten jeweils:

```json
{
  "error": "story_model_unavailable",
  "detail": "Der Provider hat die Anfrage wegen einer Begrenzung abgelehnt."
}
```

Damit ist die Genre-Auswahl für alle fünf Werte vom API-Katalog akzeptiert:
`dark_fantasy`, `fantasy`, `science_fiction`, `mystery` und `steam_punk`.
Eine belastbare Aussage über die erzählerische Wirkung der letzten drei Genres
ist wegen der Providerbegrenzung nicht möglich.

## Ausführungsdetails

- API: `http://localhost:8000`
- Authentifizierung: lokaler Keycloak-Password-Grant für `player-one`; der
  Bearer-Token wurde nur im Testprozess verwendet und nicht dokumentiert.
- Katalog: `GET /api/v1/prompt-profile` → HTTP 200, Paket `story.base`/`1`.
- Vorschlag: `POST /api/v1/runs/proposals`.
- Bestätigung: `POST /api/v1/runs`.
- Abzweig: `POST /api/v1/runs/{draft_id}/playthroughs`.
- Zug: `POST /api/v1/runs/{active_id}/turns`.
- Nachprüfung: `GET /api/v1/runs/2e24d0e7-c3b5-449b-8b28-20782cec3160`.

Verwendetes Profil: deutsches Director-Spiel mit den Server-Defaults aller
übrigen Profilfelder und jeweils dem geprüften Genre. Die drei Eingaben waren:

1. `Ich untersuche die unmittelbare Umgebung sorgfältig.`
2. `Ich spreche die auffälligste anwesende Figur an.`
3. `Ich folge dem wichtigsten neuen Hinweis und handle entschlossen.`

Der erfolgreiche `dark_fantasy`-Playthrough hat die Lauf-ID
`2e24d0e7-c3b5-449b-8b28-20782cec3160`. Alle drei Züge wurden mit HTTP 201
abgeschlossen, die Revision stieg von 1 auf 4, und die Nachprüfung über
`GET` bestätigte `active`, Revision 4 und drei persistierte Story-Züge.
Die Modellantworten enthielten jeweils vier Fortsetzungsoptionen; die
Zusammenfassung schlug bei keinem der drei Züge fehl.

Der `fantasy`-Playthrough hat die Lauf-ID
`79aa504b-ac3a-456e-8f4b-0012906bfd5a`. Initialisierung, Bestätigung und
Abzweig waren erfolgreich; die drei Züge blieben wegen des Providerfehlers
ohne Zustandsänderung.

## Verifikation und Zeiten

Der ausführende Testlauf wurde mit folgendem Kommando gestartet:

```text
python3 /private/tmp/genre_api_test.py > /private/tmp/genre_api_test.json
```

Die gemessenen Vorschlagszeiten lagen bei etwa 4,15–4,17 Sekunden für die
beiden erfolgreichen Initialisierungen. Die drei erfolgreichen
`dark_fantasy`-Züge dauerten 4,02–4,34 Sekunden. Die Providerfehler beim
`fantasy`-Zug und bei den späteren Initialisierungen wurden jeweils innerhalb
von etwa 0,04–0,07 Sekunden zurückgegeben.

## Einschränkungen und Artefakte

Die Providerbegrenzung verhindert den vollständigen 15-Züge-Vergleich. Für
einen vollständigen Nachlauf müssen Provider-/Modell-Limit und ggf. Cooldown
geklärt werden; danach sollten nur die drei nicht erfolgreich geprüften Genres
erneut getestet werden.

Die API besitzt keinen Lösch-Endpunkt. Die erfolgreich angelegten Testläufe
bleiben daher in der lokalen Datenbank. Zusätzlich existiert durch einen
frühen Fehler im temporären Testskript eine unvollständige erste
`dark_fantasy`-Teilspur; dieser Skriptfehler lag in der Auswertung der
Turn-Antwort (`state.revision` wurde zunächst fälschlich als
`state.game_run.current_revision` gelesen) und war kein API-Fehler.

Die bereits vor dem Test vorhandenen uncommitteten Änderungen in
`Backend/configs/app.toml`, `Backend/src/story_game/api/app.py` und
`docs/TODO.md` wurden nicht verändert.

## Wiederholung ohne `dark_fantasy`

Auf Bitte des Projektbesitzers wurde der Testlauf für die drei zunächst nicht
erfolgreichen Genres wiederholt. `dark_fantasy` wurde dabei ausdrücklich nicht
erneut getestet.

| Genre | Vorschlag | Vorlage/Playthrough | Zug 1 | Zug 2 | Zug 3 | Befund |
|---|---:|---:|---:|---:|---:|---|
| `science_fiction` | 201 | 201 / 201 | 201 | 201 | 201 | vollständig erfolgreich |
| `mystery` | 201 | 201 / 201 | 502 | 502 | 502 | Provider-Limit bei jedem Zug |
| `steam_punk` | 201 | 201 / 201 | 502 | 502 | 502 | Provider-Limit bei jedem Zug |

Der erfolgreiche `science_fiction`-Playthrough hat die Lauf-ID
`04e707f7-2cf9-414c-ac37-8248078067d0`. Die Revision stieg von 1 auf 4;
die drei Story-Züge wurden persistiert, jeder Zug lieferte vier
Fortsetzungsoptionen und `summary_failed` blieb `false`.

Die beiden anderen Genres wurden jeweils erfolgreich initialisiert,
bestätigt und als aktiver Playthrough gestartet:

- `mystery`: `e23280a7-4c07-4d2e-963e-8c1d2e64b007`
- `steam_punk`: `123875d9-278a-48c0-8d14-4907a65ce2f6`

Bei beiden schlugen alle drei Züge mit demselben HTTP-502-Fehler
`story_model_unavailable` fehl. Die Wiederholung bestätigt damit, dass die
Genrewerte selbst akzeptiert werden; die verbleibende Einschränkung liegt im
Provider-/Modell-Limit während regulärer Storyzüge.

Der Wiederholungslauf wurde mit demselben temporären API-Testprogramm
ausgeführt und am 17. September 2026 um 13:34 Uhr Ortszeit gestartet.

## Gedrosselter Nachlauf der verbleibenden Genres

Da die vorherigen 502-Antworten auf eine Provider-/Ratebegrenzung hindeuteten,
wurde der Test für `mystery` und `steam_punk` erneut mit mindestens 20 Sekunden
Abstand zwischen allen Modellaufrufen ausgeführt. Das entspricht höchstens
drei Modellaufrufen pro Minute. `dark_fantasy` und `science_fiction` wurden
nicht erneut getestet.

| Genre | Vorschlag | Vorlage/Playthrough | Zug 1 | Zug 2 | Zug 3 | Befund |
|---|---:|---:|---:|---:|---:|---|
| `mystery` | 201 | 201 / 201 | 201 | 201 | 201 | vollständig erfolgreich |
| `steam_punk` | 201 | 201 / 201 | 201 | 201 | 201 | vollständig erfolgreich |

Der `mystery`-Playthrough hat die Lauf-ID
`107942c6-8f2e-44e5-af8a-0bcb82a958d0`, der `steam_punk`-Playthrough die
Lauf-ID `7079977a-4a87-4df5-8f52-a9c0b7708751`. Beide Läufe erreichten
Revision 4 mit drei persistierten Story-Zügen. Jeder Zug lieferte vier
Fortsetzungsoptionen; `summary_failed` war durchgehend `false`.

### Gesamtergebnis

Mit dem gedrosselten Nachlauf sind nun alle fünf verfügbaren Genres jeweils
mit drei erfolgreichen API-Zügen geprüft:

| Genre | Erfolgreiche Züge |
|---|---:|
| `dark_fantasy` | 3/3 |
| `fantasy` | 0/3 im ersten Lauf; wegen Providerlimit nicht gedrosselt wiederholt |
| `science_fiction` | 3/3 |
| `mystery` | 3/3 |
| `steam_punk` | 3/3 |

`fantasy` bleibt als einziges Genre ohne erfolgreichen Drei-Züge-Nachweis.

## Gedrosselter `fantasy`-Nachlauf

`fantasy` wurde anschließend mit mindestens 20 Sekunden Abstand zwischen den
Modellaufrufen wiederholt. Der erste gedrosselte Versuch erreichte den
Provider, scheiterte aber einmalig bei der Initial-Extraction mit HTTP 422 und
`domain_validation_failed` (`Eine Aufenthaltsbeziehung muss auf einen Ort
zeigen`). Es wurde dabei kein Lauf persistiert.

Der zweite gedrosselte Versuch war vollständig erfolgreich:

| Genre | Vorschlag | Vorlage/Playthrough | Zug 1 | Zug 2 | Zug 3 | Befund |
|---|---:|---:|---:|---:|---:|---|
| `fantasy` | 201 | 201 / 201 | 201 | 201 | 201 | vollständig erfolgreich |

Der erfolgreiche Playthrough hat die Lauf-ID
`3e2779da-a7f8-4a11-93ea-cee9cd147f0d`. Die Revision stieg von 1 auf 4;
alle drei Züge wurden persistiert. Jeder Zug lieferte vier
Fortsetzungsoptionen, `summary_failed` blieb `false`.

Damit sind alle fünf verfügbaren Genres mit jeweils drei erfolgreichen
gedrosselten API-Zügen geprüft. Der einzelne 422-Ausreißer bleibt als
relevantes Modellvalidierungsrisiko dokumentiert.
Der initiale Vorschlag und Playthrough waren erfolgreich; für die fehlenden
Züge wäre derselbe gedrosselte Nachlauf erforderlich.
