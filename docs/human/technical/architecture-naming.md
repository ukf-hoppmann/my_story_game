# Benennung der Application-Komposition

Dieses Dokument legt die Begriffe fest, mit denen die hierarchische
Komposition und Ausführung von Application Operations beschrieben wird. Es
ergänzt den verbindlichen Architekturvertrag in
`.harness/architecture-rules.md` um eine gemeinsame Sprache für Planung,
Reviews und technische Kommunikation.

## Ebenen und Rollen

| Ebene / Rolle | Bevorzugter Name | Aufgabe | Beispiel |
| --- | --- | --- | --- |
| Verdrahtung außerhalb der Ausführung | `Composition Root` | Erstellt und verbindet den Objektgraphen mit konkreten Implementierungen | Startkonfiguration oder Dependency Wiring |
| Baustein für diese Verdrahtung | `Composition Builder` | Baut den Objektgraphen aus Operations und ihren Dependencies | Erzeugt `InitializeGameRun` mit seinen Collaborators |
| Oberste ausführbare Ebene | `Top-Level Composite` | Einstiegspunkt des fachlichen Gesamt-Workflows | `InitializeGameRun` |
| Verschachtelte ausführbare Ebene | `Composite Level X` | Komponiert und delegiert an weitere Operations | `InitializeStory` |
| Einzelne ausführbare Ebene | `Leaf` | Führt einen konkreten fachlichen oder technischen Schritt aus | `GenerateInitialStoryState` |
| Gemeinsamer Ausführungsvertrag | `Operation Contract` | Definiert den einheitlichen Einstieg über `apply(request)` | `Operation`-Protocol |
| Über Constructor übergebene Abhängigkeit | `Injected Collaborator` | Wird von einer Operation verwendet, aber nicht von ihr erzeugt | `story_generation` |
| Aufruf einer untergeordneten Operation | `Delegation` | Übergibt typisierte Eingaben an die nächste Operationsebene | `InitializeStory.apply(...)` |

`Composition Root` und `Composition Builder` gehören zur Erstellung und
Verdrahtung des Objektgraphen. `Top-Level Composite`, `Composite Level X` und
`Leaf` beschreiben dagegen die später ausgeführte Application-Struktur.

`Composition Builder` ist ein projektinterner Rollenname. Er bezeichnet den
Baustein, der den Objektgraphen aufbaut; er ist nicht das gemeinsame Interface
der ausführbaren Operations. In allgemeiner Fachsprache kann ein solcher
Baustein auch als Factory oder Dependency-Wiring-Modul bezeichnet werden.

## Standardausführungspunkt

Jede ausführbare Application Operation stellt den `Operation Contract` bereit:

```python
def apply(self, request: RequestT) -> OperationResult[DataT, ErrorT]: ...
```

Der Constructor gehört nicht zum Ausführungsvertrag. Er dient der
`Constructor Injection`: Eine Operation erhält ihre `Injected Collaborators`
vor der Ausführung und speichert sie. `apply` führt anschließend die bereits
vorbereitete Operation aus und darf nicht zu einem versteckten Service Locator
oder einer Dependency Factory werden.

Das Ergebnis folgt dem geschlossenen Result Contract:

```text
Success[DataT] | Failure[ErrorT]
```

Damit sind Eingabe, Ausführung und Ergebnis einer Operation unabhängig von der
jeweiligen Hierarchieebene typisiert.

## Beispiel aus der Story-Initialisierung

```text
Composition Root
└── Composition Builder
    └── Top-Level Composite: InitializeGameRun
        ├── Composite Level 1: InitializeStory
        │   ├── Leaf: GenerateInitialStoryState
        │   └── Leaf: ExtractInitialWorldState
        └── Leaf: CreateGameRun
```

Der Laufzeitfluss wird dabei so beschrieben:

```text
InitializeGameRun.apply(...)
└── delegiert an InitializeStory.apply(...)
    ├── delegiert an GenerateInitialStoryState.apply(...)
    └── delegiert an ExtractInitialWorldState.apply(...)
└── delegiert an CreateGameRun.apply(...)
```

Die Composite Operations legen die fachlich sichtbare Reihenfolge fest.
Leaves führen jeweils einen konkreten Schritt aus. Eine `Composition Root`
oder ein `Composition Builder` darf diese Reihenfolge nicht als versteckten
Workflow im Constructor festlegen.

## Kurzform für Kommunikation

Für Architekturgespräche gelten folgende Formulierungen als eindeutig:

- „Das Problem liegt im `Top-Level Composite`."
- „`InitializeStory` ist ein `Composite Level 1`."
- „Die Modellanfrage ist ein `Leaf`."
- „Die Abhängigkeit wird per `Constructor Injection` als `Injected Collaborator` übergeben."
- „Die nächste Ebene wird über den `Operation Contract` mit `apply` delegiert."
- „Die konkrete Verdrahtung gehört in den `Composition Builder` innerhalb der `Composition Root`."

