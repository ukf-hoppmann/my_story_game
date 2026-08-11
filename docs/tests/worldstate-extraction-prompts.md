# Prompt-Testpaket: WorldState-Extraction

Dieses Dokument enthält experimentelle, direkt in LM Studio einsetzbare
Prompts und erwartete JSON-Antworten für die WorldState-Extraction.

> **Historischer Hinweis:** Das hier getestete ChangeSet-Schema ist nicht der
> Vertrag für `STORY-009`. Die beschlossene Initial-Extraction verwendet nur
> Entitäten, Beziehungen und Fakten mit lokalen Referenzen. Evidenz,
> Sichtbarkeit, Wissen, Weltregeln und Goals sind dort kein Modelloutput. Der
> verbindliche Vertrag steht in
> [`.harness/architecture/llm-integration.md`](../../.harness/architecture/llm-integration.md)
> und der aktuelle Umsetzungsplan in
> [`docs/llm/planned/story-initialization.md`](../llm/planned/story-initialization.md).

Die Modellantwort ist immer nur ein ungeprüfter Änderungsvorschlag. Sie darf
niemals direkt in den kanonischen `WorldState` geschrieben werden. Die
Anwendung muss Schema, Referenzen, Sichtbarkeit, Basisrevision und fachliche
Invarianten prüfen und erst danach einen `ApprovedChangeSet` erzeugen.

## Einordnung

Verbindliche Grundlage sind `docs/domain-model.md`, `docs/persistence.md`,
`src/story_game/domain/world.py`, `src/story_game/domain/changes.py` und
`.harness/architecture-rules.md`.

Die JSON-Form dieses Dokuments ist ein experimenteller Testvertrag, noch kein
verbindlicher API-Vertrag. Insbesondere sind `new:`-IDs nur temporäre
Extraction-Referenzen; stabile IDs muss die Anwendung erzeugen.

Ein `slug` ist hier lediglich ein kurzer, innerhalb genau einer Modellantwort
lesbarer Bezeichner wie `merchant-iven`. `new:merchant-iven` erlaubt anderen
Änderungen derselben Antwort, auf dieses noch nicht angelegte Objekt zu
verweisen. Die Application löst alle solchen Referenzen gemeinsam auf, erzeugt
für kanonische Objekte UUIDs und verwirft den gesamten Candidate bei
unbekannten oder doppelten Referenzen. Weder der `new:`-Wert noch der Slug wird
als StableId in Domain, API oder PostgreSQL übernommen.

Auch die sprechenden `run_id`-, `turn_id`- und Proposal-Werte in den folgenden
historischen Beispielen sind Bestandteil dieses alten experimentellen Formats,
nicht Beispiele des aktuellen UUID-API-Vertrags. Evidence-Referenzen sind
transiente Reviewtexte und werden nicht kanonisch gespeichert.

Die Planungsnotiz schließt persistierte Scenes aus. Deshalb erzeugen die
Prompts keine Scenes, Events, Chapters, Threads oder Zusammenfassungen. Der
aktuelle Checkout enthält allerdings `Scene` innerhalb des `StoryState`; diese
Abweichung muss vor einer späteren Implementierung ausdrücklich geklärt werden.

## Gemeinsames Ausgabeformat

Alle WorldState-Varianten geben genau ein JSON-Objekt zurück:

```json
{
  "schema_version": "world-extraction.v1-experimental",
  "run_id": "string",
  "base_revision": 1,
  "source": {
    "turn_id": "string",
    "story_prose_id": "string"
  },
  "changes": [
    {
      "id": "proposal-change-1",
      "operation": "create_entity | update_entity | add_link | remove_link | add_fact | grant_knowledge",
      "payload": {},
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Kurzer Beleg aus der Prosa."
      },
      "visibility": {
        "scope": "public | player_known | actor_known | director_only",
        "actor_id": null
      },
      "confidence": "high | medium | low",
      "uncertainty": null
    }
  ],
  "uncertainties": [
    {
      "text": "Nicht eindeutig auflösbare Beobachtung.",
      "candidate_references": [],
      "reason": "Warum keine sichere Änderung erzeugt wurde.",
      "confidence": "low"
    }
  ],
  "ignored_observations": []
}
```

### Payload-Beispiele

```json
{
  "operation": "create_entity",
  "payload": {
    "id": "new:merchant-iven",
    "kind": "character",
    "label": "Iven",
    "description": "Ein verschwundener Händler.",
    "actor": { "role": "npc" },
    "conditions": [],
    "aliases": ["Händler Iven"]
  }
}
```

```json
{
  "operation": "update_entity",
  "payload": {
    "id": "watchman",
    "kind": "character",
    "label": "Wachmann",
    "description": "Ein misstrauischer Wächter.",
    "actor": { "role": "npc" },
    "conditions": [],
    "aliases": ["Hafenwache", "Hanno"]
  }
}
```

```json
{
  "operation": "add_link",
  "payload": {
    "id": "new:watchman-iven",
    "source_id": "watchman",
    "target_id": "new:merchant-iven",
    "kind": "knows",
    "quantity": null,
    "description": "Der Wachmann kennt Iven.",
    "visibility": { "scope": "public", "actor_id": null }
  }
}
```

```json
{
  "operation": "remove_link",
  "payload": { "link_id": "mara-lantern" }
}
```

```json
{
  "operation": "add_fact",
  "payload": {
    "id": "new:fact-merchant-missing",
    "statement": "Iven ist seit drei Nächten verschwunden.",
    "subject_id": "new:merchant-iven",
    "evidence": {
      "source": "story_prose",
      "reference": "turn-3",
      "excerpt": "Iven ist seit drei Nächten verschwunden."
    },
    "visibility": { "scope": "player_known", "actor_id": null }
  }
}
```

```json
{
  "operation": "grant_knowledge",
  "payload": {
    "actor_id": "mara",
    "fact_id": "new:fact-merchant-missing",
    "learned_at": 3,
    "forgotten_at": null
  }
}
```

## Gemeinsamer Testzustand

Diesen JSON-Block in jede WorldState-Variante als `CURRENT_WORLD_STATE`
einsetzen:

```json
{
  "run_id": "run-ashfall",
  "base_revision": 2,
  "player_actor_id": "mara",
  "world_state": {
    "entities": [
      {
        "id": "mara",
        "kind": "character",
        "label": "Mara",
        "description": "Eine neugierige Ermittlerin auf der Suche nach einem verschwundenen Händler.",
        "actor": { "role": "player" },
        "conditions": [
          {
            "name": "alert",
            "description": "Mara ist aufmerksam und bereit, Spuren zu verfolgen."
          }
        ],
        "aliases": ["Mara Voss"]
      },
      {
        "id": "watchman",
        "kind": "character",
        "label": "Wachmann",
        "description": "Ein misstrauischer Wächter, der die Ankunft jedes Schiffes beobachtet.",
        "actor": { "role": "npc" },
        "conditions": [],
        "aliases": ["Hafenwache"]
      },
      {
        "id": "harbor",
        "kind": "location",
        "label": "Alter Hafen",
        "description": "Ein verfallener Kai am Rand der Stadt.",
        "actor": null,
        "conditions": [],
        "aliases": ["Kai"]
      },
      {
        "id": "backpack",
        "kind": "item",
        "label": "Lederrucksack",
        "description": "Ein abgenutzter Rucksack mit mehreren Fächern.",
        "actor": null,
        "conditions": [],
        "aliases": ["Rucksack"]
      },
      {
        "id": "sword",
        "kind": "item",
        "label": "Hafenschwert",
        "description": "Ein schmales Schwert mit einer vom Salz angegriffenen Scheide.",
        "actor": null,
        "conditions": [
          {
            "name": "wrapped",
            "description": "Die Klinge ist in einem Tuch verborgen."
          }
        ],
        "aliases": ["Klinge"]
      },
      {
        "id": "lantern",
        "kind": "item",
        "label": "Hafenlaterne",
        "description": "Eine kleine Laterne mit rußgeschwärztem Glas.",
        "actor": null,
        "conditions": [],
        "aliases": ["Lampe"]
      }
    ],
    "links": [
      {
        "id": "mara-harbor",
        "source_id": "mara",
        "target_id": "harbor",
        "kind": "located_in",
        "quantity": null,
        "description": "Mara wartet am Kai auf Hinweise."
      },
      {
        "id": "mara-backpack",
        "source_id": "mara",
        "target_id": "backpack",
        "kind": "possesses",
        "quantity": 1,
        "description": "Der Rucksack gehört Mara."
      },
      {
        "id": "backpack-sword",
        "source_id": "backpack",
        "target_id": "sword",
        "kind": "contains",
        "quantity": 1,
        "description": "Das Schwert liegt im Hauptfach."
      },
      {
        "id": "mara-watchman",
        "source_id": "mara",
        "target_id": "watchman",
        "kind": "knows",
        "quantity": null,
        "description": "Der Wachmann kennt Mara vom Sehen."
      },
      {
        "id": "mara-lantern",
        "source_id": "mara",
        "target_id": "lantern",
        "kind": "possesses",
        "quantity": 1,
        "description": "Mara trägt die gefundene Laterne."
      }
    ],
    "facts": [
      {
        "id": "sword-hidden",
        "statement": "Das Hafenschwert befindet sich im Lederrucksack.",
        "subject_id": "sword"
      },
      {
        "id": "lantern-found",
        "statement": "Mara hat die Hafenlaterne gefunden.",
        "subject_id": "lantern"
      }
    ],
    "knowledge": [
      {
        "actor_id": "mara",
        "fact_id": "sword-hidden",
        "learned_at": 1,
        "forgotten_at": null
      },
      {
        "actor_id": "mara",
        "fact_id": "lantern-found",
        "learned_at": 2,
        "forgotten_at": null
      }
    ],
    "rules": [
      {
        "id": "night-rule",
        "statement": "Nach Einbruch der Dunkelheit bleibt das Hafentor geschlossen."
      }
    ]
  }
}
```

## Gemeinsamer Systemprompt für WorldState-Varianten

Diesen Text als LM-Studio-Systemprompt verwenden und direkt mit einem der
Fokusblöcke ergänzen:

```text
Du bist ein konservativer World-State-Extractor für ein Storygame.

Vergleiche die neue Story-Prosa mit dem mitgelieferten kanonischen WorldState
und erzeuge ausschließlich ungeprüfte, strukturierte Änderungsvorschläge.

Deine Ausgabe ist kein freigegebener Zustand. Du darfst den kanonischen
WorldState niemals selbst verändern, speichern oder als aktualisiert
bezeichnen. Eine Anwendungsschicht prüft deine Ausgabe später und erzeugt
erst danach einen ApprovedChangeSet.

Verbindliche Grenzen:
- Extrahiere nur ausdrücklich erzählte oder direkt beobachtbare Informationen.
- Leite keine Änderungen aus Atmosphäre, Stil, Vermutungen oder Möglichkeiten ab.
- Erzeuge keine Scene, kein Event, kein Chapter, keinen Thread, kein Goal und
  keine Story-Zusammenfassung.
- Erzeuge keine Weltregel.
- Erzeuge keine Entitätslöschung.
- Erhalte den mitgelieferten Zustand vollständig als maßgebliche Grundlage.

Erlaubte operation-Werte:
- create_entity
- update_entity
- add_link
- remove_link
- add_fact
- grant_knowledge

Referenzen:
- Verwende eine bestehende ID nur bei eindeutiger Zuordnung über ID, Label,
  Alias oder Kontext.
- Bei unbekannten oder mehrdeutigen Referenzen keine Änderung erzeugen;
  stattdessen uncertainties verwenden.
- Eine neue Entität nur bei eindeutiger Einführung erzeugen.
- Für neue Entitäten ausschließlich deterministische IDs im Format
  new:<kurzer-slug> verwenden. Keine UUIDs und keine Zufallswerte.
- Andere Änderungen derselben Antwort dürfen auf new:-IDs verweisen. Die
  Anwendung löst diese temporären IDs später auf.

Entitäts- und Beziehungsregeln:
- update_entity enthält den vollständigen neuen Entitätsstand, keinen Patch.
- Der Typ einer bestehenden Entität darf nicht wechseln.
- Eine Beziehungsänderung wird als remove_link plus add_link ausgegeben.
- located_in verweist auf einen Ort.
- possesses hat einen Akteur als source und ein Item als target.
- contains darf keinen Ort als target enthalten.
- Eine Entität darf nur einen aktuellen Aufenthaltsort besitzen.
- Ein Item darf nur einen aktuellen Besitzer besitzen.

Evidenz und Unsicherheit:
- Jede Änderung benötigt einen kurzen Beleg aus der Prosa.
- confidence ist high, medium oder low.
- Unsichere Aussagen gehören unter uncertainties und nicht als sichere Änderung
  unter changes.
- Formulierungen wie „vielleicht“, „vermutlich“ oder „ich glaube“ sind keine
  bestätigten Fakten.

Sichtbarkeit:
- public nur für ausdrücklich öffentliche oder beobachtbare Informationen.
- player_known, wenn ausdrücklich beschrieben wird, dass die Spielfigur davon
  weiß.
- actor_known nur mit actor_id und nur bei ausdrücklich akteurspezifischem
  Wissen.
- director_only nicht für bloße Vermutungen verwenden.
- Bei unklarer Sichtbarkeit confidence senken und uncertainty ergänzen.

Keine Änderung:
Wenn im gewählten Fokus keine sichere Änderung vorliegt, muss changes ein
leeres Array sein.

Antworte ausschließlich mit genau einem gültigen JSON-Objekt nach dem
vorgegebenen Schema. Verwende keine Markdown-Codeblöcke und keine Erklärung
außerhalb des JSON.
```

## Variante 1: Gemeinsamer WorldState-Extractor

### Fokusblock

```text
Prüfe Entitäten, Beziehungen, Fakten und akteursbezogenes Wissen gemeinsam.
Extrahiere nur WorldState-Änderungen. Wenn Änderungen voneinander abhängen,
gib sie in dieser Reihenfolge aus: neue Entitäten, entfernte alte
Beziehungen, neue Beziehungen, Fakten, Wissen.
```

### Eingabevorlage

```text
RUN_ID: {{run_id}}
BASE_REVISION: {{base_revision}}
PLAYER_ACTOR_ID: {{player_actor_id}}
CURRENT_WORLD_STATE:
{{world_state_json}}
TURN_ID: {{turn_id}}
STORY_PROSE_ID: {{story_prose_id}}
NEW_STORY_PROSE:
{{story_prose}}
```

### Beispielprosa

```text
Am dritten Abend sagt der Wachmann zu Mara: „Der Händler Iven ist seit drei
Nächten verschwunden. Ich habe ihn zuletzt bei den Lagerhäusern gesehen.“
Mara legt die Laterne auf eine Kiste am Kai und beschließt, nach Iven zu
suchen.
```

### Erwartete Antwort

```json
{
  "schema_version": "world-extraction.v1-experimental",
  "run_id": "run-ashfall",
  "base_revision": 2,
  "source": {
    "turn_id": "turn-3",
    "story_prose_id": "story-turn-3"
  },
  "changes": [
    {
      "id": "proposal-change-1",
      "operation": "create_entity",
      "payload": {
        "id": "new:merchant-iven",
        "kind": "character",
        "label": "Iven",
        "description": "Ein Händler, der seit drei Nächten verschwunden ist.",
        "actor": { "role": "npc" },
        "conditions": [],
        "aliases": ["Händler Iven"]
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Der Händler Iven ist seit drei Nächten verschwunden."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-change-2",
      "operation": "remove_link",
      "payload": { "link_id": "mara-lantern" },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Mara legt die Laterne auf eine Kiste am Kai."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-change-3",
      "operation": "add_link",
      "payload": {
        "id": "new:lantern-harbor",
        "source_id": "lantern",
        "target_id": "harbor",
        "kind": "located_in",
        "quantity": null,
        "description": "Die Hafenlaterne liegt auf einer Kiste am Kai.",
        "visibility": { "scope": "public", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Mara legt die Laterne auf eine Kiste am Kai."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-change-4",
      "operation": "add_fact",
      "payload": {
        "id": "new:fact-merchant-missing",
        "statement": "Iven ist seit drei Nächten verschwunden.",
        "subject_id": "new:merchant-iven",
        "evidence": {
          "source": "story_prose",
          "reference": "turn-3",
          "excerpt": "Der Händler Iven ist seit drei Nächten verschwunden."
        },
        "visibility": { "scope": "public", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Der Händler Iven ist seit drei Nächten verschwunden."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-change-5",
      "operation": "grant_knowledge",
      "payload": {
        "actor_id": "mara",
        "fact_id": "new:fact-merchant-missing",
        "learned_at": 3,
        "forgotten_at": null
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Der Wachmann sagt zu Mara, dass Iven verschwunden ist."
      },
      "visibility": { "scope": "actor_known", "actor_id": "mara" },
      "confidence": "high",
      "uncertainty": null
    }
  ],
  "uncertainties": [
    {
      "text": "die Lagerhäuser",
      "candidate_references": [],
      "reason": "Kein kanonischer Ort passt eindeutig; ein neuer Ort wurde nicht eindeutig eingeführt.",
      "confidence": "medium"
    }
  ],
  "ignored_observations": [
    "Mara beschließt, nach Iven zu suchen; daraus wird in dieser WorldState-Variante kein Goal erzeugt."
  ]
}
```

## Variante 2: Items

### Fokusblock

```text
Extrahiere ausschließlich Änderungen an Gegenständen und deren aktuellen
Besitz-, Inhalts- oder Aufenthaltsbeziehungen.

Erlaubt sind create_entity oder update_entity für kind=item, add_link und
remove_link für possesses, contains und located_in sowie add_fact, wenn die
Tatsache unmittelbar den Gegenstand betrifft.

Erzeuge keine Charaktere, Orte, Goals oder allgemeinen Beziehungen. Bei einer
Besitz- oder Ortsänderung muss der alte aktuelle Link entfernt und der neue
Link hinzugefügt werden.
```

### Beispielprosa

```text
Am Morgen nimmt Mara die Laterne aus ihrer Hand und verstaut sie im
Lederrucksack. Dabei springt das rußgeschwärzte Glas, aber die Laterne
funktioniert noch.
```

### Erwartete Antwort

```json
{
  "schema_version": "world-extraction.v1-experimental",
  "run_id": "run-ashfall",
  "base_revision": 2,
  "source": { "turn_id": "turn-3", "story_prose_id": "story-turn-3" },
  "changes": [
    {
      "id": "proposal-item-1",
      "operation": "remove_link",
      "payload": { "link_id": "mara-lantern" },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Mara verstaut sie im Lederrucksack."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-item-2",
      "operation": "add_link",
      "payload": {
        "id": "new:backpack-lantern",
        "source_id": "backpack",
        "target_id": "lantern",
        "kind": "contains",
        "quantity": 1,
        "description": "Die Hafenlaterne liegt im Lederrucksack.",
        "visibility": { "scope": "player_known", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Mara verstaut sie im Lederrucksack."
      },
      "visibility": { "scope": "player_known", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-item-3",
      "operation": "update_entity",
      "payload": {
        "id": "lantern",
        "kind": "item",
        "label": "Hafenlaterne",
        "description": "Eine kleine Laterne mit gesprungenem, rußgeschwärztem Glas.",
        "actor": null,
        "conditions": [
          {
            "name": "cracked_glass",
            "description": "Das Glas ist gesprungen, aber die Laterne funktioniert noch."
          }
        ],
        "aliases": ["Lampe"]
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Das rußgeschwärzte Glas springt, aber die Laterne funktioniert noch."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    }
  ],
  "uncertainties": [],
  "ignored_observations": []
}
```

Test für keine Änderung:

```text
Mara betrachtet ihre Laterne im Mondlicht und denkt über den verschwundenen
Händler nach.
```

Erwartung: `changes` ist leer; Betrachtung und Nachdenken begründen keine
sichere Item-Änderung.

## Variante 3: Characters

### Fokusblock

```text
Extrahiere ausschließlich Änderungen an Charakteren, Kreaturen und Fraktionen
sowie direkte Beziehungen zwischen ihnen.

Erlaubt sind create_entity für eindeutig neue Akteure, update_entity mit dem
vollständigen Entitätsstand, add_link und remove_link für knows, allied_with,
hostile_to, member_of und related_to sowie add_fact für unmittelbar belegte
Akteursfakten.

Ein neuer Name einer bestehenden Figur ist zunächst als möglicher Alias zu
prüfen. Erzeuge keine zweite Figur, wenn der Kontext dieselbe Figur nahelegt.
„Der Fremde“ ist ohne weitere Eindeutigkeit keine neue Entität.
```

### Beispielprosa

```text
Der Wachmann nimmt seine Kapuze ab und stellt sich als Hanno vor. Er erzählt
Mara, dass er den Händler Iven seit Jahren kennt und ihn vor drei Nächten
zuletzt gesehen hat.
```

### Erwartete Antwort

```json
{
  "schema_version": "world-extraction.v1-experimental",
  "run_id": "run-ashfall",
  "base_revision": 2,
  "source": { "turn_id": "turn-3", "story_prose_id": "story-turn-3" },
  "changes": [
    {
      "id": "proposal-character-1",
      "operation": "update_entity",
      "payload": {
        "id": "watchman",
        "kind": "character",
        "label": "Wachmann",
        "description": "Ein misstrauischer Wächter, der die Ankunft jedes Schiffes beobachtet.",
        "actor": { "role": "npc" },
        "conditions": [],
        "aliases": ["Hafenwache", "Hanno"]
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Der Wachmann stellt sich als Hanno vor."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-character-2",
      "operation": "create_entity",
      "payload": {
        "id": "new:merchant-iven",
        "kind": "character",
        "label": "Iven",
        "description": "Ein Händler, den der Wachmann seit Jahren kennt.",
        "actor": { "role": "npc" },
        "conditions": [],
        "aliases": ["Händler Iven"]
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Er erzählt Mara, dass er den Händler Iven seit Jahren kennt."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-character-3",
      "operation": "add_link",
      "payload": {
        "id": "new:watchman-iven",
        "source_id": "watchman",
        "target_id": "new:merchant-iven",
        "kind": "knows",
        "quantity": null,
        "description": "Der Wachmann kennt Iven seit Jahren.",
        "visibility": { "scope": "public", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Er ... kennt den Händler Iven seit Jahren."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    }
  ],
  "uncertainties": [],
  "ignored_observations": [
    "Das Abnehmen der Kapuze wird nicht als persistierter Charakterzustand übernommen."
  ]
}
```

## Variante 4: Locations und Beziehungen

### Fokusblock

```text
Extrahiere Orte und aktuelle Beziehungen zwischen Entitäten.

Erlaubt sind create_entity für eindeutig neue Orte, add_link und remove_link
für located_in, possesses, contains, member_of, knows, allied_with,
hostile_to und related_to sowie update_entity für ausdrücklich belegte
Änderungen an einem Ort.

Eine Ortsbewegung ist immer remove_link des bisherigen located_in-Links plus
add_link des neuen located_in-Links. Eine Scene wird niemals erzeugt.
Deiktische Angaben wie „dort“ oder „in der Nähe“ dürfen nur bei genau einer
möglichen Auflösung verwendet werden.
```

### Beispielprosa

```text
Bei Sonnenaufgang verlässt Mara den Alten Hafen und geht zum Markt am Nordtor.
Der Wachmann bleibt am Kai zurück. Zwischen dem Hafen und dem Markt liegt eine
schmale Gasse.
```

### Erwartete Antwort

```json
{
  "schema_version": "world-extraction.v1-experimental",
  "run_id": "run-ashfall",
  "base_revision": 2,
  "source": { "turn_id": "turn-3", "story_prose_id": "story-turn-3" },
  "changes": [
    {
      "id": "proposal-location-1",
      "operation": "create_entity",
      "payload": {
        "id": "new:north-gate-market",
        "kind": "location",
        "label": "Markt am Nordtor",
        "description": "Ein Markt am Nordtor der Stadt.",
        "actor": null,
        "conditions": [],
        "aliases": ["Markt"]
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Mara geht zum Markt am Nordtor."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-location-2",
      "operation": "remove_link",
      "payload": { "link_id": "mara-harbor" },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Mara verlässt den Alten Hafen."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-location-3",
      "operation": "add_link",
      "payload": {
        "id": "new:mara-market",
        "source_id": "mara",
        "target_id": "new:north-gate-market",
        "kind": "located_in",
        "quantity": null,
        "description": "Mara befindet sich am Markt am Nordtor.",
        "visibility": { "scope": "public", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Mara geht zum Markt am Nordtor."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-location-4",
      "operation": "add_link",
      "payload": {
        "id": "new:watchman-harbor",
        "source_id": "watchman",
        "target_id": "harbor",
        "kind": "located_in",
        "quantity": null,
        "description": "Der Wachmann bleibt am Kai zurück.",
        "visibility": { "scope": "public", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Der Wachmann bleibt am Kai zurück."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-location-5",
      "operation": "add_link",
      "payload": {
        "id": "new:harbor-market",
        "source_id": "harbor",
        "target_id": "new:north-gate-market",
        "kind": "related_to",
        "quantity": null,
        "description": "Eine schmale Gasse verbindet den Hafen mit dem Markt.",
        "visibility": { "scope": "public", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Zwischen dem Hafen und dem Markt liegt eine schmale Gasse."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "medium",
      "uncertainty": null
    }
  ],
  "uncertainties": [],
  "ignored_observations": []
}
```

`related_to` ist hier eine experimentelle schwache Beziehung. Ob die Gasse
als eigene Ortsentität modelliert werden sollte, bleibt eine spätere
Domainentscheidung.

## Variante 5: Fakten und Wissen

### Fokusblock

```text
Extrahiere ausschließlich bestätigungsbedürftige Fakten und explizite
Wissenszuordnungen.

Ein Fakt benötigt eine eigene ID, Aussage, Evidenz, Sichtbarkeit und optional
subject_id. Eine KnowledgeEntry bedeutet, dass ein bestimmter Akteur diesen
Fakt ab einer Story-Sequenz kennt.

Erzeuge keinen Fakt aus einer bloßen Vermutung. Wenn eine Aussage mit
„vielleicht“, „vermutlich“ oder „ich glaube“ markiert ist, gehört sie unter
uncertainties. Eine neue Entität darf nur bei eindeutiger Einführung per
create_entity angelegt werden.
```

### Beispielprosa

```text
Der Wachmann sagt zu Mara: „Iven ist seit drei Nächten verschwunden. Seine
letzte Spur führte zu den Lagerhäusern.“ Mara glaubt ihm und notiert sich den
Namen.
```

### Erwartete Antwort

```json
{
  "schema_version": "world-extraction.v1-experimental",
  "run_id": "run-ashfall",
  "base_revision": 2,
  "source": { "turn_id": "turn-3", "story_prose_id": "story-turn-3" },
  "changes": [
    {
      "id": "proposal-fact-1",
      "operation": "create_entity",
      "payload": {
        "id": "new:merchant-iven",
        "kind": "character",
        "label": "Iven",
        "description": "Ein Händler, der seit drei Nächten verschwunden ist.",
        "actor": { "role": "npc" },
        "conditions": [],
        "aliases": ["Händler Iven"]
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Iven ist seit drei Nächten verschwunden."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-fact-2",
      "operation": "add_fact",
      "payload": {
        "id": "new:fact-iven-missing",
        "statement": "Iven ist seit drei Nächten verschwunden.",
        "subject_id": "new:merchant-iven",
        "evidence": {
          "source": "story_prose",
          "reference": "turn-3",
          "excerpt": "Iven ist seit drei Nächten verschwunden."
        },
        "visibility": { "scope": "player_known", "actor_id": null }
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Iven ist seit drei Nächten verschwunden."
      },
      "visibility": { "scope": "player_known", "actor_id": null },
      "confidence": "high",
      "uncertainty": null
    },
    {
      "id": "proposal-fact-3",
      "operation": "grant_knowledge",
      "payload": {
        "actor_id": "mara",
        "fact_id": "new:fact-iven-missing",
        "learned_at": 3,
        "forgotten_at": null
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Der Wachmann sagt zu Mara, dass Iven verschwunden ist."
      },
      "visibility": { "scope": "actor_known", "actor_id": "mara" },
      "confidence": "high",
      "uncertainty": null
    }
  ],
  "uncertainties": [
    {
      "text": "die Lagerhäuser",
      "candidate_references": [],
      "reason": "Kein kanonischer Ort mit diesem Namen vorhanden; kein neuer Ort wurde eindeutig eingeführt.",
      "confidence": "medium"
    }
  ],
  "ignored_observations": [
    "Mara glaubt dem Wachmann; daraus folgt keine zusätzliche Bestätigung über die Aussage."
  ]
}
```

## Variante 6: Goals als StoryState-Sidecar

Goals gehören zum `StoryState`, nicht zum `WorldState`. Diese Variante sollte
deshalb separat oder als klar markierter Sidecar ausgeführt werden.

### Systemprompt

```text
Du bist ein konservativer Goal-Extractor für ein Storygame.

Erzeuge ausschließlich ungeprüfte Vorschläge für Goals des StoryState. Du
darfst den kanonischen GameState nicht verändern und keine Änderung als
freigegeben darstellen.

Erzeuge ein Goal nur bei ausdrücklich genannter Absicht, Aufgabe oder einem
konkreten Vorhaben. Gedanken, Hoffnungen und Atmosphäre reichen nicht.

Erlaubt sind nur add_goal und update_goal. Nicht erlaubt sind Entitäten,
Beziehungen, Fakten, Wissen, Scenes, Events, Chapters, Threads und
Zusammenfassungen.

Ein Goal benötigt id, title, owner_id, status, progress und
related_entity_ids. Bestehende Goals sind anhand von ID, Titel und
Beziehungen wiederzuverwenden; keine Duplikate erzeugen.

Neue Goal-IDs müssen im Format new:<kurzer-slug> vorliegen. Keine UUIDs oder
Zufallswerte. Unbekannte Entitätsreferenzen gehören unter uncertainties.

Antworte ausschließlich mit genau einem gültigen JSON-Objekt ohne Markdown.
```

### Beispielprosa

```text
Mara sagt: „Ich werde Iven finden und herausfinden, was mit ihm geschehen ist.“
Sie nimmt sich vor, morgen bei den Lagerhäusern zu beginnen.
```

### Erwartete Antwort

```json
{
  "schema_version": "story-goal-extraction.v1-experimental",
  "run_id": "run-ashfall",
  "base_revision": 2,
  "source": { "turn_id": "turn-3", "story_prose_id": "story-turn-3" },
  "changes": [
    {
      "id": "proposal-goal-1",
      "operation": "add_goal",
      "payload": {
        "id": "new:goal-find-iven",
        "title": "Finde Iven und kläre sein Verschwinden",
        "owner_id": "mara",
        "status": "active",
        "progress": 10,
        "related_entity_ids": ["harbor"]
      },
      "evidence": {
        "source": "story_prose",
        "reference": "turn-3",
        "excerpt": "Ich werde Iven finden und herausfinden, was mit ihm geschehen ist."
      },
      "visibility": { "scope": "public", "actor_id": null },
      "confidence": "high",
      "uncertainty": "Iven besitzt im aktuellen WorldState noch keine kanonische ID."
    }
  ],
  "uncertainties": [
    {
      "text": "Iven",
      "candidate_references": [],
      "reason": "Die Figur muss zunächst durch den WorldState-Extractor angelegt oder aufgelöst werden.",
      "confidence": "medium"
    },
    {
      "text": "Lagerhäuser",
      "candidate_references": [],
      "reason": "Der Ort ist unbekannt.",
      "confidence": "medium"
    }
  ],
  "ignored_observations": []
}
```

## Fehlerfall-Regeln

### Keine Änderung

Bei bloßer Atmosphäre, Wiederholung oder nicht persistierbaren Gedanken:

```json
{
  "changes": [],
  "uncertainties": [],
  "ignored_observations": [
    "Keine sichere Änderung im gewählten Fokus."
  ]
}
```

### Unbekannte Referenz

Nicht automatisch eine neue Entität erzeugen:

```json
{
  "text": "die Lagerhäuser",
  "candidate_references": [],
  "reason": "Kein bekannter Ort passt eindeutig.",
  "confidence": "low"
}
```

### Update statt Duplikat

„Der Wachmann stellt sich als Hanno vor“ ist normalerweise ein
`update_entity` für `watchman` mit zusätzlichem Alias. Eine neue Entität ist
nur gerechtfertigt, wenn ausdrücklich eine zweite Figur eingeführt wird, etwa:
„Ein zweiter Wachmann namens Hanno tritt aus dem Tor.“

### Unsicherheit

„Vielleicht hat der Händler den Hafen heimlich verlassen“ erzeugt keinen
Fakt. Die Aussage gehört unter `uncertainties`, weil die Prosa sie selbst als
Vermutung markiert.

## Testempfehlung

Für kleinere lokale Modelle zuerst die Item-Variante verwenden. Sie hat wenige
Entitätstypen, klare Linkwechsel und gut prüfbare Antworten. Danach folgen
Characters und Locations/Beziehungen. Der gemeinsame Extractor ist realistischer,
aber wegen der gleichzeitigen Unterscheidung mehrerer Operationstypen
fehleranfälliger.

Typische Fehlerbilder sind erfundene Entitäten, fehlende `remove_link`-Schritte,
Duplikate trotz Alias, Vermischung von `knows` und `KnowledgeEntry`, Fakten aus
 Vermutungen, ungültige `new:`-Referenzen und Markdown statt reinem JSON.
