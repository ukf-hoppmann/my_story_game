# Geplante technische Umsetzungen

Hier liegen technische Zielbilder und Umsetzungsbeschreibungen, die noch nicht
vollständig im Code oder in der Datenbank umgesetzt sind.

Jedes Dokument muss deutlich zwischen aktuellem Stand, Zielbild,
Abnahmekriterien und offenen Entscheidungen unterscheiden. Konkrete
verschobene oder noch nicht begonnene Arbeiten werden zusätzlich im
autoritativen [`docs/TODO.md`](../../../TODO.md) geführt.

Offene technische Zielbilder:

- [`story-initialization.md`](story-initialization.md): initialen StoryState
  aus einem Userprompt erzeugen, bevor ein WorldState existiert.
- [`story-generation.md`](story-generation.md): anbieterunabhängige
  Story-Erzeugung über den gemeinsamen Modellaufruf.

Die Zielbilder für Spielzustand, Persistenz und
[`native UUID-Identitäten`](stable-uuid-identities.md) wurden umgesetzt und in
die aktuellen Dokumente `domain-model.md`, `persistence.md` und `api.md`
übernommen.
