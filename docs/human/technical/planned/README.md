# Geplante technische Umsetzungen

Hier liegen technische Zielbilder und Umsetzungsbeschreibungen, die noch nicht
vollständig im Code oder in der Datenbank umgesetzt sind.

Jedes Dokument muss deutlich zwischen aktuellem Stand, Zielbild,
Abnahmekriterien und offenen Entscheidungen unterscheiden. Konkrete
verschobene oder noch nicht begonnene Arbeiten werden zusätzlich im
autoritativen [`docs/TODO.md`](../../../TODO.md) geführt.

Offene technische Zielbilder:

- [`stable-uuid-identities.md`](stable-uuid-identities.md): interne
  Storygame-Identitäten nativ als UUID führen und von textuellen Fremd- und
  Konfigurationsreferenzen trennen.
- [`story-initialization.md`](story-initialization.md): initialen StoryState
  aus einem Userprompt erzeugen, bevor ein WorldState existiert.
- [`story-generation.md`](story-generation.md): anbieterunabhängige
  Story-Erzeugung über den gemeinsamen Modellaufruf.

Das frühere Zielbild für Spielzustand und Persistenz wurde umgesetzt und in die
aktuellen Dokumente `domain-model.md`, `persistence.md` und `api.md` übernommen.
