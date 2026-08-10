# Story-Initialisierung und initiale WorldState-Extraction

Status: `STORY-008` erzeugt bereits einen transienten StoryState. Die
Spielercharakter- und Modusregeln sowie `STORY-009` sind beschlossen und für
die nächste Umsetzung geplant. Persistenz und öffentlicher Startendpunkt bleiben
Folgearbeiten.

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

Erst ein späterer Workflow darf beide Ergebnisse gemeinsam als GameRun und
GameState in Revision 1 persistieren. Der erste reguläre Spielerzug bleibt
StoryTurn 1.

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
| `third_person_limited` | erlaubt, genau ein Spielercharakter | erlaubt, kein Spielercharakter |
| `third_person_omniscient` | erlaubt, genau ein Spielercharakter | erlaubt, kein Spielercharakter |

`third_person_limited + player` bleibt ein normaler Singleplayer-Modus. Er
bezeichnet nicht automatisch Multiplayer.

Der bisherige Director-Prompt beschreibt nur einen Handlungsspielraum des
Erzählmodells und überschneidet sich damit mit `player_agency`. Die Umsetzung
muss seine Bedeutung korrigieren:

- `player`: Der User kontrolliert genau eine Spielerfigur.
- `director`: Der User dirigiert die Szene oder mehrere Figuren; es gibt keine
  dedizierte Spielerfigur.

Im Director Mode wird `player_agency` nicht an das Modell übergeben und später
in der UI ausgeblendet oder deaktiviert. Die GameConfiguration darf den Wert
vorerst weiterhin vollständig speichern.

## Vom User angelegter Spielercharakter

Der Spielercharakter ist ein vertrauenswürdiger Initialisierungsinput und kein
Modellergebnis:

```text
PlayerCharacterSeed
├── name: erforderlich
└── description: optional
```

Im Player Mode ist genau ein Seed erforderlich. Im Director Mode ist ein Seed
ungültig. Eine ungültige Kombination erzeugt einen typisierten, blockierenden
Application-Fehler, bevor ein Modell aufgerufen wird. Die spätere UI kann
diesen Fehler als verständliche Warnung darstellen; ohne gültige Auswahl geht
der Workflow nicht weiter.

Der Seed gehört nicht in den StoryState. Die übergeordnete Operation hält ihn
zwischen Story-Erzeugung und WorldState-Extraction und erstellt daraus im
WorldState eine `WorldEntity` vom Typ `character` mit `ActorRole.PLAYER`.

## Story-Erzeugung

`GenerateInitialStoryState` bleibt ein eigener providerneutraler Prozess. Sein
Modellrequest enthält:

- Story-Initialisierungs-Systemprompts;
- die aufgelöste GameConfiguration einschließlich Sprache und gültiger
  Erzähloptionen;
- den freien Initialprompt;
- den PlayerCharacterSeed im Player Mode.

Er enthält keinen WorldState und keine bisherige Story-Chronologie. Das Modell
darf den vorgegebenen Spielercharakter erzählerisch verwenden, aber weder
auswählen noch umbenennen.

## Initiale Extraction

`ExtractInitialWorldState` ist ein anderer Modellauftrag mit eigenem Port,
Prompt und strukturiertem Ergebnis. Der Modellrequest enthält ausschließlich:

- Extraction-Systemprompts;
- die Eröffnungsprosa als Goldstandard dafür, was passiert ist;
- das JSON-Response-Schema;
- Sprache, Perspektive und Control Mode;
- den PlayerCharacterSeed als bekannte Entität im Player Mode.

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
└── facts
    ├── statement
    └── subject_ref
```

Das Modell erzeugt keine StableIds. Die Application löst lokale Referenzen auf
und vergibt IDs erst nach erfolgreicher Strukturprüfung.

## Charaktere im Extraction-Ergebnis

Das Modell darf in jeder Perspektive weitere Charaktere extrahieren, muss aber
keinen zurückgeben. Auch `entities = []` ist gültig.

- Der vorgegebene Spielercharakter ist kein Extraction-Ergebnis.
- Beziehungen und Fakten dürfen ihn über die reservierte Referenz
  `player_character` ansprechen.
- Eine Modell-Entität darf diese Referenz nicht selbst belegen.
- Eine exakte Namens- oder Aliasduplikation des Spielercharakters wird
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
- eine mögliche Duplikation des vorgegebenen Spielercharakters;
- erlaubte Entitäts- und Beziehungstypen;
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

Der ausdrücklich aktivierte Live-Test verwendet einen konkreten
PlayerCharacterSeed, führt beide Modellprozesse aus und gibt aus:

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
