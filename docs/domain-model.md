# Domainmodell des Storygames

Die Domain-Schicht bildet den kanonischen Zustand eines Storygame-Laufs ab.
Sie kennt weder Datenbank, API noch LLM.

## Aggregatgrenze

`GameState` ist die Aggregatwurzel. Er enthält zwei getrennte fachliche
Bereiche:

- `WorldState`: stabile Entitäten, Beziehungen, Fakten, Wissen und Weltregeln.
- `StoryState`: Ereignisse, Szenen, Kapitel, Threads, Ziele und abgeleitete
  Zusammenfassungen.

World-Fakten und dramaturgischer Fortschritt werden dadurch nicht zu einem
unstrukturierten Memory-Dokument vermischt.

## Kanonische Daten

`WorldEntity` besitzt eine stabile Identität und einen typisierten Entitätstyp.
Aufenthalt, Besitz, Behälter, Zugehörigkeit und soziale Verbindungen werden als
`EntityLink` modelliert. Das Inventar wird aus Besitzbeziehungen abgeleitet.

`Fact` beschreibt ausschließlich bestätigte kanonische Aussagen. `Evidence`
und `Visibility` machen nachvollziehbar, worauf eine Aussage beruht und wer sie
kennen darf. `KnowledgeEntry` ordnet einen Fakt einem konkreten Akteur zu.

`StoryEvent` ist nach der Übernahme chronologisch und unveränderlich. Eine
`Scene` führt nur die tatsächlich anwesenden Entitäten. `StoryThread` und
`Goal` unterscheiden offene Handlungsstränge von konkreten Zielen.

## Zustandsänderungen

Das Modell liefert Prosa und unbestätigte `ProposedChangeSet`-Objekte. Diese
sind nicht Teil des kanonischen Zustands. Erst die Anwendung prüft Schema,
Referenzen, Sichtbarkeit, geschützte Fakten und die Basisrevision und erzeugt
daraus einen `ApprovedChangeSet`.

Nur ein freigegebener Änderungssatz kann über `GameState.apply` eine neue
State-Revision erzeugen. Ein direktes Anwenden von Modell- oder Roh-JSON ist
nicht vorgesehen.

## Bewusst außerhalb der Domain-Schicht

Kampfregeln, Würfel, Level, Wirtschaft, Prompt-Konfiguration, LLM-Aufrufe,
Persistenz und API-Transportmodelle gehören nicht in die Domain-
Implementierung. Die PostgreSQL- und JSON-Adapter liegen deshalb getrennt in
der Infrastruktur; die API und die LLM-Anwendungsfälle werden später als
eigene Schichten ergänzt.
