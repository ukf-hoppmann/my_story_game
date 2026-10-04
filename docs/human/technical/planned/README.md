# Geplante technische Umsetzungen

Hier liegen technische Zielbilder und Umsetzungsbeschreibungen. Ein Dokument
kann dabei einen bereits umgesetzten Kern mit noch offenen Ausbaupunkten
beschreiben; der aktuelle Status muss am Anfang des jeweiligen Dokuments
erkennbar sein.

Jedes Dokument muss deutlich zwischen aktuellem Stand, Zielbild,
Abnahmekriterien und offenen Entscheidungen unterscheiden. Konkrete
verschobene oder noch nicht begonnene Arbeiten werden zusätzlich im
autoritativen [`docs/todo/TODO.md`](../../../todo/TODO.md) geführt.

Dokumente mit verbleibenden Ziel- oder Ausbaupunkten:

- [`story-initialization.md`](story-initialization.md): initialen StoryState
  und WorldState aus einem Userprompt erzeugen. Der Workflow ist umgesetzt;
  offene Punkte betreffen vor allem Modellqualität und spätere UI-/Kontroll-
  entscheidungen.
- [`story-generation.md`](story-generation.md): anbieterunabhängige
  Story-Erzeugung über den gemeinsamen Modellaufruf. Der vollständige
  Storyzug ist umgesetzt; offen bleiben ausgewählte Ausbaupunkte wie
  historische Kontextdaten, automatischer Review und weitere Provider.

Die Zielbilder für Spielzustand, Persistenz und
[`native UUID-Identitäten`](stable-uuid-identities.md) wurden umgesetzt und in
die aktuellen Dokumente `domain-model.md`, `persistence.md` und `api.md`
übernommen.
