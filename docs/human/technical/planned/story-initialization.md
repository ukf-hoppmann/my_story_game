# Story-Initialisierung und initiale WorldState-Extraction

Status: `STORY-008`, `STORY-009` und `STORY-010` sind umgesetzt und
verifiziert. `InitializeStory` liefert StoryState und WorldState transient als
gemeinsames Ergebnis. Die Lauf-API verwendet darüber den zweistufigen
Workflow `ProposeGameRun` und `ConfirmGameRunProposal`: Erstere Operation
hält die Eröffnung als owner-gebundenen, ablaufenden Vorschlag vor; erst die
Bestätigung persistiert den initialen `GameRun` atomar. Der öffentliche
Startendpunkt gehört zu `STORY-003`.

Nachtrag: Director Mode ist kein Modus ohne steuerbare Figur mehr, sondern
erlaubt 0..N explizit benannte steuerbare Figuren (siehe TASK-016). Player
Mode bleibt der Sonderfall mit genau einer. Die folgenden Abschnitte
beschreiben deshalb `ControllableCharacterSeed` als Liste, nicht mehr als
optionalen Einzelwert.

Der echte LM-Studio-Test führt beide Aufrufe aus und druckt Eingaben,
Rohantworten und Endzustände. Das lokale Modell erzeugt technisch nutzbare
Candidates, verletzt in der Eröffnungsprosa aber noch sichtbar die strenge
Player-Agency und zerlegt Prosa teilweise in zu viele Fakten. Die Application
behält deshalb ihre strikte all-or-nothing-Prüfung; es gibt weder automatischen
Retry noch stilles Reparieren eines ungültigen Candidates.

## Zielbild

Ein User startet eine Geschichte mit einer GameConfiguration, einem freien
Initialprompt und – im Player Mode – einem selbst angelegten Charakter. Eine
übergeordnete Application-Operation führt danach zwei getrennte Modellprozesse
aus:

```text
InitializeStory
├── GenerateInitialStoryState
│   └── transienter StoryState mit Eröffnungsprosa
└── ExtractInitialWorldState
    └── transienter, validierter WorldState
```

`ProposeGameRun` persistiert dabei noch nichts. `ConfirmGameRunProposal`
persistiert die bestätigten Ergebnisse gemeinsam als GameRun und GameState in
Revision 1. Der Run startet im Status `DRAFT`; der aufrufende Benutzer erhält
die `OWNER`-Mitgliedschaft. `GameRunMember.controlled_entity_ids` verweist auf
alle `ActorRole.PLAYER`-Entitäten des WorldState, die aus den übergebenen
Seeds entstanden sind — im Player Mode genau eine, im Director Mode 0..N.
Alle internen IDs sind native UUIDs. Der erste reguläre Spielerzug bleibt
StoryTurn 1 und erzeugt Revision 2.

## Perspektive und Control Mode

Die beiden Auswahlachsen haben verschiedene Aufgaben:

- `perspective` bestimmt, wie erzählt wird.
- `control_mode` bestimmt, was der User kontrolliert.
- `player_agency` bestimmt nur im Player Mode, wie stark das Modell Handlungen
  der Spielerfigur vorwegnehmen darf.

Multiplayer ist keine Perspektive und kein Control Mode. Eine spätere
Mehrspielerunterstützung benötigt eigene Mitgliedschafts- und
Charakterzuordnungen.

Für die vorhandenen Perspektiven gelten:

| Perspektive | Player Mode | Director Mode |
|---|---|---|
| `first_person` | erlaubt, genau ein Spielercharakter | ungültig |
| `second_person` | erlaubt, genau ein Spielercharakter | ungültig |
| `third_person_limited` | erlaubt, genau ein Spielercharakter | erlaubt, 0..N steuerbare Figuren |
| `third_person_omniscient` | erlaubt, genau ein Spielercharakter | erlaubt, 0..N steuerbare Figuren |

`third_person_limited + player` bleibt ein normaler Singleplayer-Modus. Er
bezeichnet nicht automatisch Multiplayer.

Der bisherige Director-Prompt beschreibt nur einen Handlungsspielraum des
Erzählmodells und überschneidet sich damit mit `player_agency`. Die Umsetzung
muss seine Bedeutung korrigieren:

- `player`: Der User kontrolliert genau eine Spielerfigur.
- `director`: Der User dirigiert die Szene und 0..N explizit benannte,
  steuerbare Figuren; alle übrigen Figuren bleiben NPCs ohne direkten
  Einfluss des Users.

Im Director Mode wird `player_agency` nicht an das Modell übergeben und später
in der UI ausgeblendet oder deaktiviert. Die GameConfiguration darf den Wert
vorerst weiterhin vollständig speichern.

## Vom User angelegte steuerbare Figuren

Jede steuerbare Figur ist ein vertrauenswürdiger Initialisierungsinput und kein
Modellergebnis:

```text
ControllableCharacterSeed
├── name: erforderlich
└── description: optional
```

Der Request trägt eine Liste `controllable_characters`. Im Player Mode ist
genau ein Seed erforderlich. Im Director Mode sind null oder mehrere Seeds
gültig, müssen sich aber im Namen unterscheiden. Eine ungültige Kombination
(falsche Anzahl für den Modus, doppelte Namen) erzeugt einen typisierten,
blockierenden Application-Fehler, bevor ein Modell aufgerufen wird. Die
spätere UI kann diesen Fehler als verständliche Warnung darstellen; ohne
gültige Auswahl geht der Workflow nicht weiter.

Die Seeds gehören nicht in den StoryState. Die übergeordnete Operation hält
sie zwischen Story-Erzeugung und WorldState-Extraction und erstellt daraus im
WorldState je eine `WorldEntity` vom Typ `character` mit `ActorRole.PLAYER`.

## Story-Erzeugung

`GenerateInitialStoryState` bleibt ein eigener providerneutraler Prozess. Sein
Modellrequest enthält:

- Story-Initialisierungs-Systemprompts;
- die aufgelöste GameConfiguration einschließlich Sprache und gültiger
  Erzähloptionen;
- den freien Initialprompt;
- die `ControllableCharacterSeed`-Liste (0..N, je nach Modus).

Er enthält keinen WorldState und keine bisherige Story-Chronologie. Das Modell
darf die vorgegebenen steuerbaren Figuren erzählerisch verwenden, aber weder
auswählen noch umbenennen.

## Initiale Extraction

`ExtractInitialWorldState` ist ein anderer Modellauftrag mit eigenem Port,
Prompt und strukturiertem Ergebnis. Der Modellrequest enthält ausschließlich:

- Extraction-Systemprompts;
- die Eröffnungsprosa als Goldstandard dafür, was passiert ist;
- das JSON-Response-Schema;
- Sprache, Perspektive und Control Mode;
- die `ControllableCharacterSeed`-Liste als bekannte, reservierte Entitäten
  (`player_character`, `player_character_2`, … in Zuordnungsreihenfolge).

Der ursprüngliche Initialprompt wird nicht erneut übergeben. Genre, Ton,
Prosa-Stil und typische Fantasy-Konventionen dürfen nicht als Weltfakten oder
Weltregeln einfließen. Es gibt noch keinen vorhandenen WorldState, mit dem das
Modell vergleichen könnte.

Das minimale Modellergebnis ist ein `WorldInitializationCandidate`:

```text
WorldInitializationCandidate
├── entities
│   ├── local_ref
│   ├── kind
│   ├── label
│   ├── description
│   ├── conditions
│   └── aliases
├── links
│   ├── source_ref
│   ├── target_ref
│   ├── kind
│   ├── quantity
│   └── description
├── facts
│   ├── statement
│   └── subject_ref
└── scene_refs
```

Das Modell erzeugt keine StableIds. Die Application löst lokale Referenzen auf
und vergibt IDs erst nach erfolgreicher Strukturprüfung.

`scene_refs` ist eine geordnete Liste lokaler Ortsreferenzen und benennt, wo die
Eröffnung spielt; der wichtigste Schauplatz steht zuerst. Das ist eine eigene
Aussage und nicht dasselbe wie `located_in`: dieses sagt, wo eine Entität ist,
`scene_refs` sagt, wohin die Erzählung blickt. Im Director Mode kann eine Szene
erzählt werden, in der die gesteuerte Figur nicht vorkommt, weshalb sich der
Schauplatz nicht aus Aufenthaltsorten ableiten lässt. Eine leere Liste ist nur
gültig, wenn die Eröffnung überhaupt keinen Ort etabliert.

## Charaktere im Extraction-Ergebnis

Das Modell darf in jeder Perspektive weitere Charaktere extrahieren, muss aber
keinen zurückgeben. Auch `entities = []` ist gültig.

- Jede vorgegebene steuerbare Figur ist kein Extraction-Ergebnis.
- Beziehungen und Fakten dürfen sie über ihre reservierte Referenz ansprechen
  (`player_character` für die erste, `player_character_2` für die zweite, …).
- Eine Modell-Entität darf keine dieser Referenzen selbst belegen.
- Eine exakte Namens- oder Aliasduplikation einer steuerbaren Figur wird
  abgewiesen.
- Vom Modell gelieferte Entitäten vom Typ `character` erhalten durch die
  Application automatisch `ActorRole.NEUTRAL`.
- Andere Entitätsarten erhalten in dieser ersten Version kein ActorProfile.

Eine semantische Duplikation unter völlig anderer Bezeichnung lässt sich ohne
weitere Modellbewertung nicht sicher ausschließen. Der Extraction-Prompt und
der Live-Test müssen dieses verbleibende Risiko sichtbar machen.

## Bewusst leere Bereiche

Die initiale Extraction erzeugt:

```text
knowledge = ()
rules = ()
goals = ()
```

- `KnowledgeEntry.learned_at` wird erst relevant, wenn Charakterwissen
  tatsächlich spielmechanisch ausgewertet wird.
- Weltregeln werden nicht aus Genre, Ton oder Konventionen abgeleitet. Sie sind
  für den jetzigen Storyfokus nicht erforderlich.
- Goals und die vorhandenen `AddGoal`-/`UpdateGoal`-Operationen bleiben für
  spätere Haupt- und Nebenquests vorbereitet, sind aber kein Teil des initialen
  Schemas.

## Evidenz und Sichtbarkeit

Evidenz beweist nicht, dass ein extrahierter Fakt wahr ist. Ohne späteren
Review- oder Auditprozess erzeugt ihre kanonische Persistenz Scheinsicherheit.
Deshalb wird Evidenz aus `Fact`, `WorldRule`, API und PostgreSQL entfernt. Da
das Projekt noch früh in der Entwicklung ist, wird dafür die Initialmigration
direkt angepasst. Bestehende Entwicklungsdatenbanken werden neu angelegt; es
gibt keine rückwärtskompatible Upgrade-Migration.

Ein späterer Review-Workflow darf Evidenz transient an einem `ProposedChange`
halten. Sie wird nach Annahme nicht automatisch in den WorldState kopiert.

Das Modell bestimmt zunächst auch keine Sichtbarkeit. Links und Fakten erhalten
den vorhandenen Domain-Default `public`. Dieser Wert ist ein technischer
Default und noch keine umgesetzte UI-Zugriffsentscheidung. Vor einer
wissensabhängigen Anzeige muss die Sichtbarkeitssemantik erneut bewertet
werden.

## Validierung und Fehler

Der LM-Studio-Adapter übermittelt ein JSON-Schema und wandelt technisch gültige
Antworten in typisierte Kandidaten um. Die Application prüft anschließend:

- reservierte und doppelte lokale Referenzen;
- alle Link- und Fact-Referenzen;
- eine mögliche Duplikation einer vorgegebenen steuerbaren Figur;
- erlaubte Entitäts- und Beziehungstypen;
- die Schauplatzreferenzen: unbekannte Referenzen, Duplikate und Verweise auf
  eine Entität, die kein Ort ist, verwerfen den gesamten Kandidaten;
- sämtliche WorldState-Domain-Invarianten.

Die Übernahme ist all-or-nothing. Provider-, Parsing-, Schema-, Referenz- oder
Domainfehler liefern einen sichtbaren typisierten Fehler. Es gibt zunächst
keinen automatischen Retry und niemals einen partiellen WorldState.

Für Extraction gilt zunächst:

```text
temperature = 0.1
max_output_tokens = None
```

## Live-Test und Persistenzgrenze

Der ausdrücklich aktivierte Live-Test verwendet konkrete
`ControllableCharacterSeed`-Werte, führt beide Modellprozesse aus und gibt
aus:

- beide tatsächlich versendeten Modellrequests einschließlich Response-Schema;
- die Modell- und Generationseinstellungen;
- die Modellantworten;
- den fertigen StoryState und WorldState als JSON.

Der Test persistiert nichts. Standardtests bleiben offline und müssen den
Live-Test ohne Aktivierungsflag überspringen. Die manuelle Verifikation führt
ihn anschließend ausdrücklich mit Aktivierungsflag gegen das bereitgestellte
LM Studio aus und verlangt einen erfolgreichen Lauf; ein bloßes Skip-Ergebnis
ist kein Live-Nachweis.

## Konkrete Umsetzungsreihenfolge

1. PlayerCharacterSeed und gültige Perspective-/Control-Kombinationen in
   STORY-008 ergänzen.
2. Persistierte Evidenz geschlossen aus Domain, API und PostgreSQL entfernen;
   transiente Review-Evidenz in der Application belassen.
3. Den strukturierten Initial-Extraction-Port und den LM-Studio-JSON-Schema-
   Adapter implementieren.
4. Kandidaten all-or-nothing in einen transienten WorldState überführen.
5. Beide Prozesse in `InitializeStory` orchestrieren.
6. Deterministische Tests, expliziten Live-Test und vollständige
   Integrationsverifikation abschließen.

Die maschinenorientierten Subtasks mit Abhängigkeiten und Akzeptanzkriterien
stehen in
[`docs/llm/planned/story-initialization.md`](../../../llm/planned/story-initialization.md).
