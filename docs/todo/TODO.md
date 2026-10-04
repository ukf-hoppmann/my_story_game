# Project Backlog

Active project work: open, in progress, or awaiting a project-owner decision.
Completed and rejected items are moved to `archive.md`; per-item notes and
specs live in `items/<ID>/`.

Format: Claude_Harness backlog format version 1. The rules are defined in the
`todo` skill of the claude-harness plugin (`skills/todo/format.md`).

## Work items

- `EPIC-001` **Storygame-Datenmodell neu implementieren**
  - Type: Epic.
  - Status: In progress.
  - Created: 2026-08-04.
  - Area: Domainmodell, Persistenz und API.
  - Priority: Important.
  - Dependencies: None.
  - Goal: Das beschlossene Datenmodell für ein Storygame in einer Onion Architecture umsetzen. Die Umsetzung erfolgt schrittweise: zuerst fachliche Domain-Entities, danach Datenbankanbindung und anschließend die produktive API.
  - Completion criteria: Die zentralen Storygame-Daten können über fachliche Domain-Entities modelliert, anschließend dauerhaft gespeichert und schließlich über eine API erstellt, gelesen und verändert werden. Kanonische Zustandsänderungen werden ausschließlich über geprüfte Anwendungslogik übernommen; das LLM erhält keinen direkten Schreibzugriff auf den GameState.

- `EPIC-002` **LLM-Anbindung und Storyzug-Workflow**
  - Type: Epic.
  - Status: In progress.
  - Created: 2026-08-07.
  - Area: LLM-Integration und Story-Workflow.
  - Priority: Important.
  - Dependencies: `EPIC-001`.
  - Goal: Einen vollständigen, providerunabhängigen Storyzug aus Modell- und Promptkatalogen, tatsächlichen Modellaufrufen, Story-Erzeugung, WorldState-Extraktion, fachlicher Freigabe und atomarem Turn-Commit zusammensetzen.
  - Completion criteria: Die sieben zugehörigen Stories sind umgesetzt und integriert. Ein vollständiger Storyzug kann zuerst aus einem Initialprompt einen StoryState und danach einen WorldState bilden, den initialen GameState atomar anlegen, den relevanten fortlaufenden GameState-Kontext verwenden, normalisierte Story-Prosa erzeugen, strukturierte Extraktionsvorschläge fachlich prüfen und ausschließlich einen abgeschlossenen StoryTurn mit der resultierenden GameState-Revision persistieren. Modellaufrufe, Rohantworten, ProposedChangeSets und Validierungsergebnisse bleiben transient.

- `TASK-028` **Repetition-Loop und Entitäts-Relevanz bei der Initial-Extraction beheben**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-009`.
  - Required for parent: No.
  - Created: 2026-08-18.
  - Area: LLM-Integration, Initial-Extraction (Prompt und Sampling).
  - Priority: Important.
  - Dependencies: `STORY-009`, `TASK-009`, `TASK-012`.
  - Goal: Der Live-Test `test_state_extract` schlägt reproduzierbar fehl, weil das
    Extraction-Modell (`llama@q4_k_m`, Temperature 0.1, striktes JSON-Schema) in
    eine Wiederholungsschleife läuft und dieselbe Handvoll Entitäten wiederholt
    ausgibt, bis das Kontextlimit erreicht und die Antwort abgeschnitten wird.
    Unabhängig davon fragmentiert der Prompt Objekte zu grob in Teil-Entitäten
    (z. B. "Griff des Schwertes" statt "Schwert") und extrahiert auch narrativ
    irrelevante, transiente Requisiten (z. B. ein Buttermesser beim
    Brotschmieren), während plotrelevante Gegenstände (ein Schwert, ein Messer
    als Waffe) korrekt als Entität geführt werden sollen. `TASK-012` hat
    Temperatur 0.1 ohne Tokenlimit bewusst bestätigt; diese Entscheidung muss
    im Licht des Repetition-Loops erneut geprüft werden, nicht stillschweigend
    überschrieben werden.
  - Completion criteria: Entschieden und umgesetzt ist, wie die Wiederholungs-
    schleife verhindert wird (z. B. Sampling-Anpassung, Modellwahl oder eine neue
    Generation-Option) und wie der Prompt Objekte nach narrativer Relevanz statt
    nach bloßer Erwähnung extrahiert, ohne plotrelevante Gegenstände wie Waffen
    zu verlieren. Der Live-Test `test_state_extract` läuft wiederholt ohne
    Abschneiden durch; der resultierende WorldState enthält keine künstlich
    fragmentierten Teil-Entitäten und keine transienten Requisiten ohne
    erwartbare Wiederverwendung. Jede Sampling- oder Modelländerung ist mit
    Begründung dokumentiert und gegen die in `TASK-012` bestätigte Entscheidung
    abgeglichen.

- `TASK-018` **Verdecktes Wissen im Story-Prompt kennzeichnen**
  - Type: Task.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Story-Workflow und Promptgestaltung.
  - Priority: Prospective.
  - Dependencies: `TASK-017`.
  - Goal: Entscheiden und umsetzen, wie dem Modell im Story-Prompt kenntlich gemacht wird, dass ein Teil des Kontexts der Spielerseite noch nicht bekannt ist. Die Kontextauswahl filtert bewusst nicht nach `Visibility`, damit das Modell auf verdeckte Ziele hinarbeiten kann; der erste Wurf von `TASK-017` kennzeichnet den Unterschied im Prompt jedoch bewusst gar nicht. Beobachtet werden muss, ob das Modell dadurch verdeckte Plotpunkte vorzeitig ausspricht.
  - Completion criteria: Es ist entschieden, welche Sichtbarkeitsstufen als verdeckt gelten — mindestens `director_only`, gegebenenfalls auch Wissen anderer Figuren — und wie sie im Prompt erscheinen; die Regel für den Director Mode ohne Spielerfigur ist festgelegt; Projektion und Promptpaket setzen sie um und sind getestet.

- `TASK-025` **Historische Daten in den Turn-Kontext aufnehmen**
  - Type: Task.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Story-Workflow.
  - Priority: Prospective.
  - Dependencies: `TASK-015`.
  - Goal: Bezugnahmen auf Vergangenes im Prompt auflösbar machen. Die Kontextauswahl liest heute ausschließlich die aktuelle Revision. Sagt der Spieler „ich gehe zurück", weiß das Modell nur dann was gemeint ist, wenn der frühere Ort zufällig noch in den letzten Zügen oder der Zusammenfassung vorkommt. Die Information liegt vollständig in der Datenbank — jede Revision hält einen kompletten Weltsnapshot, alte Revisionen werden nie gelöscht — sie erreicht nur den Prompt nicht.
  - Completion criteria: Entschieden und umgesetzt ist, welcher historische Ausschnitt in den Kontext gelangt — mindestens der vorherige Schauplatz, gegebenenfalls frühere Aufenthaltsorte oder entfernte Tatsachen. Die Auswahl bleibt deterministisch und budgetiert; die Herkunft der historischen Daten ist im Prompt als solche erkennbar, damit das Modell Vergangenes nicht als Gegenwart erzählt.

- `TASK-026` **Automatischen Review der Änderungsvorschläge einführen**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-007`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Story-Workflow und Diagnose.
  - Priority: Important.
  - Dependencies: `TASK-021`.
  - Goal: Vorgeschlagene Änderungen automatisch und ohne nennenswerte Rechenlast auf Plausibilität prüfen, statt sie nur strukturell zu validieren. Der Review läuft ohne Benutzereingriff und hält den Spielfluss nicht an; seine Befunde sollen optional anzeigbar sein, damit sichtbar wird, wie oft und wobei das Modell danebenliegt.
  - Completion criteria: Das Delta-Schema führt je Änderung einen Beleg als wörtliches Zitat aus der Erzählung. Deterministische Prüfungen erzeugen je Änderung Befunde: der Beleg kommt in der Erzählung tatsächlich vor; die Bezeichnung einer neu vorgeschlagenen Entität ist in der Erzählung auffindbar; ein neuer Schauplatz ist genannt oder unverändert. Die vorhandene deutschsprachige Namenserkennung wird dafür wiederverwendet, statt eine zweite zu bauen. Befunde sind Hinweise, keine Ablehnung — strukturelle Fehler und Domainverstöße verwerfen den Vorschlag weiterhin ganz. Die Befunde sind abrufbar und im Live-Test sichtbar. Dokumentiert ist, was der automatische Review ausdrücklich nicht leisten kann.

- `TASK-031` **Gegenstände im Wizard-Review einer Figur zuordnen können**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-14.
  - Area: Web-Frontend (Wizard), API und Domainmodell.
  - Priority: Important.
  - Dependencies: None.
  - Goal: Im Review-Schritt des Wizards kann ein vorgeschlagener Gegenstand aktuell nur entfernt werden ([Wizard.tsx:533-557](Frontend-Web/src/routes/Wizard/Wizard.tsx:533), `ItemDecisionState` in [wizardSlice.ts:24](Frontend-Web/src/features/wizard/wizardSlice.ts:24) kennt nur `removed`; ebenso serverseitig `ItemDecision` in [confirm_game_run_proposal.py:49](Backend/src/story_game/application/confirm_game_run_proposal.py:49)). Stattdessen soll jeder Gegenstand bei der Erstellung frei einer beliebigen vorgeschlagenen Figur (Spieler oder NPC) zugeordnet werden können, analog zur bestehenden Spieler/NPC-Rollenwahl bei Figuren ([Wizard.tsx:501-527](Frontend-Web/src/routes/Wizard/Wizard.tsx:501)). Zusätzlich wird eine neue Warnung eingeführt, wenn ein Gegenstand noch keiner Figur zugeordnet ist — diese Warnung darf frühestens erscheinen, nachdem der Nutzer die Rollenwahl der Figuren (Spieler/NPC) abgeschlossen hat, nicht schon vorher (z. B. nicht sofort beim Laden des Vorschlags oder während die Figuren noch unentschieden sind).
    - Ergänzung (2026-09-17): Ein Sonderfall der Zuordenbarkeit ist bislang nicht abgedeckt: Der Spielercharakter existiert als eigene vorgeschlagene Figur nur, wenn er im Story-Text explizit genannt/erwähnt wurde; wurde er nicht explizit genannt, gibt es zum Zeitpunkt des Reviews noch keine Figur-Entity für den Spieler, der ein Gegenstand zugeordnet werden könnte. Ohne Sonderbehandlung würde ein Gegenstand, der eigentlich dem Spieler gehören soll, in diesem Fall zwangsläufig unzugeordnet bleiben (und die neue Warnung auslösen), obwohl der Nutzer inhaltlich weiß, wem er gehört. Zu klären: ob/wie eine "Spieler"-Zuordnungsoption auch dann angeboten wird, wenn (noch) keine explizite Spielerfigur im Vorschlag existiert (z. B. durch implizites Anlegen der Spielerfigur bei Bedarf, oder durch eine generische "gehört dem Spieler"-Option unabhängig von der Figurenliste).
  - Completion criteria: `ItemDecision` (Frontend und Backend) trägt zusätzlich zu `removed` eine optionale Besitzer-Entity-ID; die Wizard-UI bietet pro Gegenstand eine Auswahl aus den nicht entfernten Figuren, analog zu den Chips der Charakter-Zuordnung. `ConfirmGameRunProposal` übernimmt die gewählte Zuordnung als `POSSESSES`-Beziehung im persistierten WorldState (siehe `RelationKind.POSSESSES` in [value_objects.py:88](Backend/src/story_game/domain/value_objects.py:88)); eine fehlende Zuordnung bleibt zulässig (Gegenstand ohne Besitzer bleibt möglich), löst aber die neue Warnung aus. Die Warnung erscheint nachweislich (Test) nicht, solange noch nicht jede Figur eine Spieler/NPC-Rolle zugewiesen bekommen hat, und erscheint danach für jeden noch nicht zugeordneten Gegenstand. Tests belegen Zuordnung, Warnung-Timing und die Übernahme der Besitzbeziehung im WorldState. Zusätzlich entschieden und getestet: Eine Zuordnung zum Spieler ist auch dann möglich, wenn der Spielercharakter im Vorschlag nicht als explizit genannte Figur vorkommt (kein Gegenstand bleibt allein aus diesem Grund zwangsweise unzugeordnet).

- `TASK-035` **Turn-Chronik im Zustand paginieren statt vollständig zu laden**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-17.
  - Area: API und Web-Frontend (Play).
  - Priority: Important.
  - Dependencies: None.
  - Goal: `GameStateModel`/`StoryStateModel.turns` ([state.py:36-37](Backend/src/story_game/api/schemas/state.py:36)) liefert aktuell bei jedem Laden des Zustands (initiales `GET /api/v1/runs/{run_id}` sowie das im `TurnResultModel` eingebettete `state` nach `POST /api/v1/runs/{run_id}/turns`, [runs.py:134-148](Backend/src/story_game/api/schemas/runs.py:134)) die vollständige Turn-Liste seit Spielbeginn. Das soll durch dynamisches Nachladen ersetzt werden: standardmäßig nur die letzten N Turns (z. B. 3), mit einer Möglichkeit für die Play-Chronik-Ansicht ([Play.tsx](Frontend-Web/src/routes/Play/Play.tsx)), beim Scrollen ältere Turns zusätzlich nachzuladen. Zu klären ist außerdem, ob `POST .../turns` weiterhin den vollständigen `state` zurückgeben soll oder nur noch Erfolg/Fehler meldet, woraufhin das Frontend den (dann paginierten) Zustand separat über den GET-Pfad nachlädt — das würde das Nachladen beim Scrollen und das initiale Laden auf denselben Mechanismus vereinheitlichen, ändert aber das bestehende `TurnResultModel`-Vertrag und dessen Konsumenten.
  - Completion criteria: Entschieden und dokumentiert ist, (1) ob und wie ein Turn-Pagination-Parameter am GET-Endpunkt aussieht (Cursor oder Offset, Seitengröße, Sortierrichtung), (2) ob `POST .../turns` weiterhin den vollständigen `state` liefert oder auf Erfolg/Fehler reduziert wird, und (3) wie das mit der bereits abschnittsweisen `story.summaries`-Kette aus `TASK-032` zusammenspielt (Zusammenfassungsabschnitte sind bereits kompakt und müssten von einer Turn-Pagination nicht zwingend betroffen sein). Nach Umsetzung: Ein Laden des Zustands überträgt nicht mehr sämtliche Turns seit Spielbeginn; die Play-Chronik kann ältere Turns bei Bedarf nachladen (z. B. beim Scrollen ans obere Ende); bestehende Turn-Reihenfolge und lückenlose Sequenznummern bleiben für den Client nachvollziehbar. Tests belegen Pagination-Verhalten (Grenzen, leere/kurze Chronik, Nachladen) sowohl API- als auch frontendseitig.

- `TASK-036` **Leere `continuation_options` zulassen statt den ganzen LLM-Call scheitern zu lassen**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-21.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Important.
  - Dependencies: `TASK-033`.
  - Goal: `TASK-033` validiert `continuation_options` in `StoryGenerationData` und `InitialStoryText` ([llm/contracts.py](Backend/src/story_game/application/llm/contracts.py)) hart als nicht-leer (`ValueError` bei leerem Tupel). Das ist strenger als die zugehörige Architekturregel in `.harness/architecture/llm-integration.md` §5/§5a, die den Optionssatz nur als "MAY also contain" führt. Liefert ein Modell legitim eine Erzählung ohne sinnvolle Fortsetzungsoptionen — etwa einen Ende-Beat oder eine Szene ohne echte Handlungsalternativen —, scheitert dadurch der gesamte Zug, statt lediglich ohne Optionen auszukommen. Zu entscheiden und umzusetzen ist, ob ein leerer Optionssatz auf Contract-Ebene zulässig wird und wie sich API und Play-UI ([Play.tsx](Frontend-Web/src/routes/Play/Play.tsx), Chip-Anzeige aus `TASK-034`) in diesem Fall verhalten.
  - Completion criteria: Entschieden und dokumentiert ist, ob `continuation_options` leer sein darf und ob Contract und Architekturregel (§5/§5a) danach übereinstimmen. Falls leer zulässig: Die Validierung in den Contracts und den Provider-Wires ([narration_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/narration_wire.py)) lässt ein leeres Tupel zu, ohne den Erzähl-Call fehlschlagen zu lassen; die API-Schemas (`ContinuationModel` in [schemas/runs.py](Backend/src/story_game/api/schemas/runs.py)) übertragen eine leere Liste; die Play-UI rendert in diesem Fall schlicht keine Chips und bleibt über das Freitextfeld voll bedienbar. Tests belegen den leeren Fall auf Contract-, Wire-, API- und Frontend-Ebene.

- `TASK-037` **Strikte JSON-Schema-Ausgabe der Erzähl-Calls live gegen alle drei Provider verifizieren**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-21.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Important.
  - Dependencies: `TASK-033`.
  - Goal: `TASK-033` hat `story_generation` und `story_initialization` von Fließtext auf striktes `response_format.json_schema` umgestellt ([narration_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/narration_wire.py), [story_generation_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/story_generation_wire.py), [story_initialization_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/story_initialization_wire.py)). Verifiziert wurde das bisher ausschließlich mit Mocks und Doubles — ob LM Studio (`openai_compatible`), Gemini und Groq das strikte Schema real zuverlässig einhalten, ist offen. Gerade bei Groq und Gemini ist die Schema-Treue erfahrungsgemäß das Risiko, und ein Verstoß träfe jeden Zug, nicht nur Randfälle.
  - Completion criteria: Für alle drei Provider ist mit echten Aufrufen belegt, dass Erzählung und `continuation_options` schemakonform zurückkommen; abweichendes Verhalten je Provider ist dokumentiert und, wo nötig, im jeweiligen Wire behandelt (z. B. Fallback oder provider-spezifische Schema-Formulierung). Die Live-Prüfung ist als ausführbarer, standardmäßig übersprungener Test hinterlegt, analog zu den bestehenden `--run-lmstudio-live`-Tests.

