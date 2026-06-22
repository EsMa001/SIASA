# SIASA – Zentrales Planungsdokument (Master-Plan)

> Dies ist das **einzige steuernde Planungsdokument** von SIASA. Es ersetzt alle früheren
> Planungsgenerationen (Master-Steering, Roadmap, Executive-View, Audit, Gap-Pläne, Level-Pläne).
> Diese sind nach `docs/plans/outdated/` archiviert und dienen nur noch als historische Referenz.
>
> **Evidenz-/Nachweis-Begleiter:** `docs/plans/siasa-capability-fulfillment-matrix.md`
> (detailliertes Status-/Test-/Probe-Ledger; wird von Produktionscode gelesen und bleibt aktiv).

Stand: 2026-06-21
Status: Aktiv – einzige Planungsquelle für die Vorwärtssteuerung

---

## 0. Wie dieses Dokument zu benutzen ist

Dieses Dokument leistet genau vier Dinge:

1. Es zeigt **alle großen Arbeitspakete und Teilarbeitspakete** in einer einheitlichen Hierarchie.
2. Es zeigt pro Paket den **Status** (erledigt / offen / blockiert / zurückgestellt).
3. Es hält eine **steuerbare Prioritätsreihenfolge** für die offenen Pakete (Abschnitt 3) – das ist die Stelle,
   an der die Projektleitung die Reihenfolge selbst festlegt.
4. Es verweist für jeden Punkt auf die **historische Herkunft** (Legacy-IDs) und die **Evidenz**.

Dokument-Hierarchie (Ebenen der Planungsdokumente):

| Ebene | Dokument | Rolle |
| --- | --- | --- |
| L0 – Planung/Steuerung | `docs/plans/siasa-master-plan.md` (dieses Dokument) | Einzige Planungsquelle: Arbeitspakete, Priorität, Status |
| L1 – Evidenz/Nachweis | `docs/plans/siasa-capability-fulfillment-matrix.md` | Detail-Ledger mit Test-/Probe-Evidenz (read-only Begleiter) |
| L2 – Historie | `docs/plans/outdated/**` | Frühere Planungsgenerationen, nur Referenz/Traceability |
| L3 – Governed Source-of-Truth | `vmodel/project/*.yaml` | Verbindliche Requirements-/WP-/Prioritäts-Artefakte |

Nicht-Regel: Wähle das nächste Arbeitspaket niemals aus den `Immediate Next Recommendation`-Abschnitten der
Dokumente unter `outdated/`. Maßgeblich ist allein Abschnitt 3 dieses Dokuments.

---

## 1. Einheitliche Namens- und Hierarchie-Konvention

Bisher existierten parallel mindestens zehn ID-Schemata (`G1–G5`, `N1-WP-001..071`, `VAL-WP-001..026`,
`WP-001..008`, `WP-001/002/003` unter G4, `P0–P4`, `Step A/B/C`, `A-/B-/C-`, `AP-F01..F27`, `AP-N01`,
`AP-19..27`). Das war die eigentliche Ursache der „Planungsgenerationen-Überlappung". Ab sofort gilt **ein**
Schema.

### 1.1 Hierarchie-Ebenen

| Ebene | Bezeichnung | ID-Schema | Beispiel |
| --- | --- | --- | --- |
| Ebene 0 | Programm | `SIASA` | SIASA |
| Ebene 1 | **Großes Arbeitspaket** (Epic) | `AP-NN` | `AP-05` |
| Ebene 2 | **Teilarbeitspaket** | `AP-NN.M` | `AP-05.3` |
| Ebene 3 | Schritt / Task (nur wo nötig) | `AP-NN.M.K` | `AP-05.3.1` |

Regeln:
- **AP-IDs sind stabile Identität.** Eine einmal vergebene Nummer wird nicht neu vergeben und ändert sich nicht,
  auch nicht bei Umpriorisierung. So bleibt Traceability erhalten.
- Neue große Arbeitspakete bekommen die nächste freie `AP-NN`, neue Teilpakete die nächste freie `AP-NN.M`.
- Das alte `WP-001..WP-008`-Schema bleibt **nur** als governed Fundament-IDs in
  `vmodel/project/implementation_workpackages.yaml` bestehen (siehe AP-01) – im Plan werden sie nicht erneut
  als `WP-xxx` geführt, um die frühere Kollision (`WP-001` = Fundament vs. `WP-001` = G4-Subpaket) aufzulösen.

### 1.2 Einheitliche Status-Werte

| Status | Bedeutung |
| --- | --- |
| `Erledigt` | Implementiert, getestet, evidenzbelegt, abgeschlossen |
| `In Arbeit` | Aktiver Default-Track; mehrere Teilpakete erledigt, weitere offen |
| `Offen` | Geplant, noch nicht begonnen |
| `Blockiert` | Repo-seitig fertig; wartet auf externen Auslöser (z. B. Credentials) |
| `Zurückgestellt` | Bewusst später / nur bei expliziter Umpriorisierung |

### 1.3 Einheitliche Prioritäts-/Klassen-Werte

- **Rang (Prio):** `P1, P2, P3, …` – die **steuerbare** Bearbeitungsreihenfolge (Abschnitt 3). Nur offene/aktive
  Pakete haben einen Rang.
- **Klasse:** governed MVP-Klassifikation aus `vmodel/project/prioritization.yaml`
  (`MVP-Must`, `MVP-Should`, `MVP-Could`, `Post-MVP`, `Out-of-Scope`).

---

## 2. Status-Dashboard (alle großen Arbeitspakete)

| AP-ID | Großes Arbeitspaket | Status | Rang | Klasse | Herkunft (Legacy) |
| --- | --- | --- | --- | --- | --- |
| AP-01 | Fundament & Kernpipeline | Erledigt | – | MVP-Must | `WP-001..008` (vmodel), `AP-F01..F27` |
| AP-02 | Runtime-Breite: governed MVP-Slice (30 Länder) | Erledigt | – | MVP-Must | `G1`, Roadmap `P0/P2`, `Step A` |
| AP-03 | Operationale Evidenz-Spur | Erledigt | – | MVP-Should | `G3`, `N1-WP-003..010` |
| AP-04 | Release-Lifecycle: Freigabe → Distribution | Erledigt | – | MVP-Should | `G4 WP-001/002/003`, `Step C` (`C-1..C-12`) |
| AP-05 | Validierungs-Realismus & Analyst-Handoff | Erledigt | – | MVP-Should | `VAL-WP-001..026`, `N1-WP-011..071`, `Step B` |
| AP-06 | Externe credential-gated Quellen-Aktivierung | Blockiert | **P2** | MVP-Should | `G2`, `P0-WP-001`, ReliefWeb/UCDP |
| AP-07 | Quellen-Robustheit & Degradations-Wahrheit | Erledigt | – | MVP-Should | `G1`-Rest, `SRC-GDELT-DOC/-E` |
| AP-08 | Breiten-Ausbau über mvp-complete hinaus | Erledigt | – | MVP-Could | Roadmap §5, Source-Origin/Epidemiologie |
| AP-09 | Server-gestützte Multi-User-Governance | Zurückgestellt | **P3** | Post-MVP | `G5` |
| AP-10 | Terminologie-Glossar & Begriffs-Normalisierung | Erledigt | – | MVP-Should | neu (kein Legacy) |
| AP-11 | Free-API-Quellen-Verbreiterung (D/E/C/A) | In Arbeit | **P1** | MVP-Could | public-apis-Analyse; freie APIs ohne Credential-Blocker |

Gesamtbild: Das Fundament und alle repo-seitig steuerbaren Gap-Familien (`G1`, `G2`, `G3`, `G4`) sind
**materiell geschlossen** (Capability-Matrix: `17/17 Done`, `100.0%`). AP-05 (Validierungs-Realismus),
AP-07 (Quellen-Robustheit), AP-08 (Breiten-Ausbau auf 88 Länder) und AP-10 (Terminologie-Glossar) sind
ebenfalls erledigt. Die verbleibende Arbeit ist freie Quellen-Verbreiterung, externe Aktivierung und –
zurückgestellt – Multi-User.

---

## 3. Prioritäts-Backlog (STEUERBAR)

> **Dies ist die Stelle, an der die Reihenfolge gesteuert wird.** Die Bearbeitungsreihenfolge ergibt sich aus
> dem `Rang`. Empfohlener Default ist unten gesetzt – frei überschreibbar.

| Rang | AP-ID | Großes Arbeitspaket | Status | Klasse | Auslöser / Bedingung |
| --- | --- | --- | --- | --- | --- |
| **P1** | AP-11 | Free-API-Quellen-Verbreiterung (D/E/C/A) | Offen | MVP-Could | freie APIs aus public-apis-Analyse; kein Credential-Blocker |
| **P2** | AP-06 | Externe Quellen-Aktivierung (G2) | Blockiert | MVP-Should | **springt auf P1**, sobald gültige ReliefWeb/UCDP-Credentials vorliegen |
| **P3** | AP-09 | Multi-User-Governance (G5) | Zurückgestellt | Post-MVP | nur wenn Operating-Model Multi-User explizit fordert |

### So steuerst du die Reihenfolge

1. **AP-IDs nicht ändern** – sie sind stabile Identität (Traceability). Gesteuert wird nur die Spalte `Rang`.
2. Zum Umpriorisieren die `Rang`-Werte ändern bzw. die Tabellenzeilen umsortieren. Die Tabelle in diesem
   Abschnitt ist die maßgebliche Reihenfolge.
3. Die Spalte „Auslöser / Bedingung" sagt, wann ein blockiertes/zurückgestelltes Paket automatisch nach oben
   rückt (z. B. AP-06 bei verfügbaren Credentials).
4. Abgeschlossene Pakete (AP-01..AP-05) haben keinen Rang und stehen nur in Abschnitt 2 und 4.

### Begründung der Default-Reihenfolge

- **AP-11 zuerst (P1):** Freie APIs ohne Credential-Blocker schließen Domain-D/E/C/A-Lücken schrittweise; jeder
  Adapter ist eigenständig wertvoll und hat kein externes Blockier-Risiko.
- **AP-06 (P2, bedingt):** Repo-seitig fertig; der einzige offene Hebel ist extern (Credentials). Sobald
  Credentials da sind, ist dies das wertvollste gebündelte Paket und springt auf P1.
- **AP-09 (P3, zurückgestellt):** Großer Architektursprung; nur bei explizitem Bedarf am Ziel-Betriebsmodell.

---

## 4. Große Arbeitspakete & Teilarbeitspakete (Detail)

Definition of Done (global, gemäß `AGENTS.md`): Implementierung + Traceability + Tests + grüne Checks +
Doku-Update + Konsistenzprüfung der Kontextartefakte. Serielle Ausführung: ein gebündeltes Teilpaket →
gezielte Tests → Full-Suite → Master-Plan/Matrix aktualisieren → Commit/Push.

### 4.A Abgeschlossenes Fundament (AP-01 … AP-04)

#### AP-01 — Fundament & Kernpipeline · Status: Erledigt · Klasse: MVP-Must
Herkunft: governed `WP-001..WP-008` (`vmodel/project/implementation_workpackages.yaml`); frühere
`AP-F01..F27`-Funktionsplanung (ausgeführt).

| TAP | Inhalt | Status | Governed-ID |
| --- | --- | --- | --- |
| AP-01.1 | Katalog- & Konfigurationsbasis | Erledigt | WP-001 |
| AP-01.2 | Source-Adapter-Framework & Failure-Isolation | Erledigt | WP-002 |
| AP-01.3 | Raw- & Normalized-Daten-Layer | Erledigt | WP-003 |
| AP-01.4 | Feature-Berechnung A/B/D | Erledigt | WP-004 |
| AP-01.5 | Baseline-, Anomalie- & Status-Engines (D0–D5, S0–S6) | Erledigt | WP-005 |
| AP-01.6 | Snapshot- & Traceability-Kern | Erledigt | WP-006 |
| AP-01.7 | Reporting- & Read-Model-Basis | Erledigt | WP-007 |
| AP-01.8 | Annotation/Validation/Governance/Reprocessing | Erledigt | WP-008 |

#### AP-02 — Runtime-Breite: governed MVP-Slice · Status: Erledigt · Klasse: MVP-Must
Herkunft: `G1`; Roadmap-Phasen `P0/P2`, `Step A`. Repo-seitig geschlossen.

| TAP | Inhalt | Status | Evidenz |
| --- | --- | --- | --- |
| AP-02.1 | Governed Live-Runtime + Pilot-Sets (core/extended/focus/mvp-complete) | Erledigt | CLI-Help + Runtime-Unit-Tests |
| AP-02.2 | Volle 30-Länder `mvp-complete`-Schließung | Erledigt | `RUN-OP-LATEST-G1-CLOSE-001` (`30/30`, `breadth_full_slice_updated`, Gate `pass`) |
| AP-02.3 | Readiness-Honesty + Domain-Governance (A/D bei Low-Signal-B) | Erledigt | `RUN-LIVE-REP-READINESS-TRUTH-001` |

#### AP-03 — Operationale Evidenz-Spur · Status: Erledigt · Klasse: MVP-Should
Herkunft: `G3`; `N1-WP-003..010`. Eine normalisierte Operator-/PL-Evidenzspur mit Frische-/Autoritäts-Status.

| TAP | Inhalt | Status | Evidenz |
| --- | --- | --- | --- |
| AP-03.1 | `operational_evidence_lane.json` + `runs.html`-Panel | Erledigt | `N1-WP-003` |
| AP-03.2 | Latest-/Archiv-Navigation, Evidenz-Links, Triage-Tags | Erledigt | `N1-WP-005..010` |
| AP-03.3 | Frische-/Autoritäts-Status (fresh/stale/override-governed) | Erledigt | `RUN-OP-LATEST-G3-CLOSE-001` |

#### AP-04 — Release-Lifecycle: Freigabe → Distribution · Status: Erledigt · Klasse: MVP-Should
Herkunft: `G4 WP-001/002/003`; `Step C` Produktisierung (`C-1..C-12`).

| TAP | Inhalt | Status | Evidenz |
| --- | --- | --- | --- |
| AP-04.1 | Lifecycle-Record + Artefakt + GUI-Panel (`release_package.html`) | Erledigt | G4 WP-001 |
| AP-04.2 | Transition-CLI (`approve/defer/reject/distribute`) + Evidence-Lane in `runs.html` | Erledigt | G4 WP-002 (`scripts/lifecycle_transition.py`) |
| AP-04.3 | Packet-Truth-Alignment: Lifecycle-Ergebnis propagiert in Sign-off/Send-Flächen | Erledigt | G4 WP-003 |
| AP-04.4 | Decision-Packet Seed + Send-Readiness-Checkliste | Erledigt | `C-11`, `C-12` |

### 4.B Offene / laufende / zurückgestellte Arbeitspakete (AP-05 … AP-09)

#### AP-05 — Validierungs-Realismus & Analyst-Handoff · Status: Erledigt · Klasse: MVP-Should
Kanonischer Track-Name (Legacy/EN): **validation realism depth / analyst handoff refinement**.
Herkunft: `VAL-WP-001..026`, `N1-WP-011..071`, Roadmap `Step B` (`B-1..B-6`).
Ziel: Non-perfekten Replay-Realismus vertiefen und den deterministischen Analyst-Handoff
(Export/Aktion/Decision-Scaffolding) stärken – ohne bereits geschlossene Runtime-/Governance-Familien
wieder zu öffnen.

| TAP | Inhalt | Status | Herkunft / Evidenz |
| --- | --- | --- | --- |
| AP-05.1 | Challenge-Case-Portfolio (Weak-Evidence/Mismatch/Domain-Gap) | Erledigt (laufend erweiterbar) | `VAL-WP-001/007/013` (32 Cases) |
| AP-05.2 | Replay-Attention-Watchlist: Sortierung, Presets, Scoping, Copy/CSV | Erledigt | `VAL-WP-005/006/008/009/012` |
| AP-05.3 | Kontext-tragende Deep-Links Briefing → Coverage/Validation/Annotation | Erledigt | `VAL-WP-014/015/016/017` |
| AP-05.4 | Annotation-Decision-Scaffolding (Typ + Decision-Posture deterministisch) | Erledigt | `N1-WP-069/070/071` |
| AP-05.5 | Reviewer-Decision-Templates in Sign-off/Routing/Send-Readiness | Erledigt | `N1-WP-071` |
| AP-05.6 | Decision-Log-/Approval-Condition-Auto-Seeds | Erledigt | Decision-log auto-seeds in release package |

DoD nächstes Slice: ein gebündeltes Validierungs-/Handoff-Slice; gezielte RED/GREEN-Tests; Full-Suite grün;
ein reales Probe-Bundle; Master-Plan + Capability-Matrix aktualisiert; Commit/Push.

#### AP-06 — Externe credential-gated Quellen-Aktivierung · Status: Blockiert (extern) · Rang: P2 · Klasse: MVP-Should
Herkunft: `G2`, `P0-WP-001` (Source-Access-Assessment, archiviert unter `outdated/`), `P0-WP-002c`.
Repo-seitig geschlossen: Adapter + graceful Degradation + Aktivierungs-/Evidenz-Wahrheit
(`activated_with_live_evidence`, `configured_but_not_evidenced`, `credentialed_but_live_fetch_failed`,
`external_blocker_present`). Offener Hebel ist rein extern (Credentials/Registrierung).

| TAP | Inhalt | Status | Bedingung |
| --- | --- | --- | --- |
| AP-06.1 | ReliefWeb live aktivieren (Domain-C-Breite) | Blockiert | benötigt `RELIEFWEB_APPNAME` (approved appname) |
| AP-06.2 | UCDP-GED live aktivieren | Blockiert | benötigt `UCDP_API_TOKEN` im Operator-Lane |
| AP-06.3 | Entscheidung über weitere fehlende Quellklassen (implementieren vs. bewusst aufschieben) | Offen | PL-Entscheid |

Auslöser-Regel: Sobald gültige Credentials vorliegen → AP-06 auf P1 ziehen, einen governed Aktivierungslauf
fahren und explizite Source-Success-Evidenz erfassen.

#### AP-07 — Quellen-Robustheit & Degradations-Wahrheit · Status: Erledigt · Klasse: MVP-Should
Herkunft: `G1`-Rest (das einzige verbliebene Delta der Runtime-Breite). Es geht **nicht** um fehlende
governed Breite, sondern um Provider-Degradations-Wahrheit und deren Release-/Readiness-Konsequenz.

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-07.1 | `SRC-GDELT-DOC` / `SRC-GDELT-DOC-E` Degradationswahrheit + Release-Konsequenz härten | Erledigt | Per-Country-Fault-Isolation, Malformed-Article-Skip, Degraded-Countries-Diagnostik; `69ca9fc` |
| AP-07.2 | Retry-/Partial-Success-Profile bei neuem Failure-Mode nachschärfen | Erledigt | Shared `retry_utils.py`, `is_retryable_error()` (429/5xx/Timeout/Connection), konfigurierbarer Timeout; `69ca9fc` |

#### AP-08 — Breiten-Ausbau über mvp-complete hinaus · Status: Erledigt · Klasse: MVP-Could
Herkunft: Roadmap §5 (Control/Reference-Restslices), Source-Origin/Epidemiologie-Groundwork (`P4`).

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-08.1 | Nächster Länder-Cluster / restliche control-reference-Slices | Erledigt | 58 neue Länder (88 total): LatAm, SEA, Afrika, Nahost, Europa, Zentralasien, Ostasien; 5 regionale Pilot-Sets; `20d0e93` |
| AP-08.2 | Source-Origin-Inferenz / Informations-Epidemiologie ausbauen | Offen | Groundwork in Traceability-View vorhanden; bewusst später |

#### AP-09 — Server-gestützte Multi-User-Governance · Status: Zurückgestellt · Rang: P3 · Klasse: Post-MVP
Herkunft: `G5`. Heutiger lokaler/statischer governed-Bundle-UX ist materiell stark; Multi-User nur bei
explizitem Bedarf am Ziel-Betriebsmodell.

| TAP | Inhalt | Status | Bedingung |
| --- | --- | --- | --- |
| AP-09.1 | Architektur-Entscheidungs-Slice (Operating-Model bestätigen, Scope authn/authz + Persistenz) | Zurückgestellt | nur bei Multi-User-Bedarf |
| AP-09.2 | Server-seitige Identität / authn / authz | Zurückgestellt | nach AP-09.1 |
| AP-09.3 | Persistierter Review-/Annotation-Workflow (Multi-User) | Zurückgestellt | nach AP-09.1 |

#### AP-10 — Terminologie-Glossar & Begriffs-Normalisierung · Status: Erledigt · Klasse: MVP-Should
Herkunft: neu (kein Legacy). Quer-Abhängigkeit zu allen Planungs- und Code-Artefakten.
Ziel: Ein maschinenlesbares Glossar mit aussagekräftigen, möglichst deutschsprachigen Bezeichnungen
mit klarer Definition, englischem Äquivalent und Zuordnung zu Code-Identifiern. Bestehende Dokumente
(Masterplan, Capability-Matrix, Code-Docstrings) werden auf konsistente Terminologie normalisiert.

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-10.1 | Glossar-Datei erstellen (`docs/glossary.yaml`) – Struktur + erste Extraktion aus Masterplan/Matrix | Erledigt | 55 Terme in 9 Kategorien, YAML-validiert |
| AP-10.2 | Begriffe aus bestehenden Planungsdokumenten extrahieren und ins Glossar aufnehmen | Erledigt | Masterplan, Capability-Matrix, AGENTS.md ausgewertet |
| AP-10.3 | Terminologie in Masterplan normalisieren (einheitliche Begriffe gemäß Glossar) | Erledigt | Masterplan bereits konsistent; keine Korrekturen nötig |
| AP-10.4 | Terminologie in Capability-Matrix normalisieren | Erledigt | Matrix bewusst englisch (wird von Code gelesen); konsistent |
| AP-10.5 | Code-Docstrings und Kommentare auf Glossar-Begriffe prüfen und ggf. ergänzen | Erledigt | 67 Code-Identifier in Glossar gemappt |

#### AP-11 — Free-API-Quellen-Verbreiterung (D/E/C/A) · Status: Offen · Rang: P1 · Klasse: MVP-Could
Herkunft: Analyse des `public-apis/public-apis`-Repos (544 APIs, 51 Kategorien), abgeglichen gegen
SIASA-Domain-Coverage-Lücken und bestehenden Quellkatalog (`vmodel/project/data_sources.yaml`).
Ziel: Schrittweise Verbreiterung der Domain-Coverage durch freie, authfreie oder apiKey-basierte
APIs — ohne die externen Credential-Blocker von AP-06. Jeder Adapter ist eigenständig wertvoll.

Priorisierung der TAPs nach Domain-Lückengröße:
- **Domain D** (Wirtschaft): größte Lücke — nur 2 World-Bank-Indikatoren
- **Domain E** (Cyber/InfoOps): nur globale CISA-KEV, kein Länderbezug
- **Domain C** (Humanitär): dünn, kein Sanctions-/Safety-Signal
- **Domain A** (Narrative): nur GDELT, keine Diversifikation

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-11.1 | `SRC-STATISTICS-WORLD` Adapter: Statistics of the World API (440+ Indikatoren, 218 Länder, IMF+WB) | Blockiert | Domain D; API liefert leere Daten (v1+v2 `data:[]`); erst nutzbar wenn API tatsächlich Daten serviert |
| AP-11.2 | `SRC-FRANKFURTER` Adapter: ECB-Wechselkurse (Frankfurter API) | Erledigt | Domain D; free, no auth, no rate limit; `api.frankfurter.dev`; 14 Tests |
| AP-11.3 | `SRC-VOIDLY` Adapter: Internet-Zensur & ISP-Blocking (130 Länder) | Erledigt | Domain E; demo-key `hydra_demo_key`; `api.voidly.ai/hydra/v1/scores`; 12 Tests |
| AP-11.4 | `SRC-OPENSANCTIONS` Adapter: Sanktionen, PEP, Kriminalität | Blockiert | Domain C; API erfordert API-Key (kein freier Zugang); Registrierung nötig |
| AP-11.5 | `SRC-WARNELY` Adapter: Composite Travel-Safety-Scores (180 Länder) | Blockiert | Domain C; API/Domain nicht mehr erreichbar (404/DNS-Fehler) |
| AP-11.6 | `SRC-HDX` Adapter: OCHA Humanitarian Data Exchange | Offen | Domain C; free; `data.humdata.org/` |
| AP-11.7 | `SRC-NEWSAPI` oder `SRC-GNEWS` Adapter: Nachrichten-Diversifikation | Offen | Domain A; free apiKey; diversifiziert GDELT-Abhängigkeit |
| AP-11.8 | Quellkatalog (`data_sources.yaml`) + Glossar aktualisieren | Offen | nach jedem neuen Adapter |

---

## 5. Offene Lücken & Blocker (Zusammenfassung)

| # | Lücke | Betroffenes AP | Art | Nächster Schritt |
| --- | --- | --- | --- | --- |
| L1 | ~~Tiefe des non-perfekten Replay-Realismus / Decision-Auto-Seeds~~ | AP-05.6 | geschlossen | AP-05 erledigt; Decision-log auto-seeds implementiert |
| L2 | ReliefWeb/UCDP nur repo-ready, nicht live aktiviert | AP-06.1/.2 | **extern blockiert** | Credentials beschaffen → AP-06 auf P1 |
| L3 | ~~GDELT-Provider-Degradation & Release-Konsequenz~~ | AP-07 | geschlossen | Per-Country-Fault-Isolation + shared retry_utils; `69ca9fc` |
| L4 | ~~Breite über die governed 30-Länder hinaus~~ | AP-08.1 | geschlossen | 88 Länder, 5 regionale Pilot-Sets; `20d0e93` |
| L5 | Multi-User/Server-Governance | AP-09 | strategisch | nur bei Operating-Model-Bedarf (P3, zurückgestellt) |
| L6 | ~~Uneinheitliche/unklare Terminologie über Planungs- und Code-Artefakte~~ | AP-10 | geschlossen | Glossar mit 55 Termen erstellt; Artefakte konsistent |
| L7 | Domain-D/E/C/A-Coverage dünn — wenige Quellen, keine Diversifikation | AP-11 | intern, offen | Free-API-Adapter schrittweise ergänzen (P1) |

Pivot-Auslöser (wann die Priorisierung neu bewertet wird):
- gültige ReliefWeb/UCDP-Credentials werden verfügbar → AP-06 hoch;
- frische Runtime-Evidenz zeigt einen neuen Steuerungs-/Wahrheitsdefekt → AP-07 hoch;
- externe Steuerung fordert Multi-User-Betrieb → AP-09 aktivieren;
- ein neuer Länder-/Quellen-Cluster wird Pflicht → AP-08 hoch;
- konkrete Analytik-Anforderung braucht breitere Domain-Coverage → AP-11 hoch.

---

## 6. Abgelöste Dokumente (Konsolidierungs-Mapping)

Alle folgenden Dokumente wurden in diesen Master-Plan konsolidiert und nach `docs/plans/outdated/` verschoben.
Sie bleiben als historische Referenz/Traceability erhalten, sind aber **nicht** mehr steuerungsmaßgeblich.

| Abgelöstes Dokument (jetzt in `outdated/`) | Frühere Rolle | Konsolidiert in |
| --- | --- | --- |
| `siasa-master-steering-document.md` | „single steering document", `G1–G5`, `N1-WP-001..071` | Abschnitte 2–5 |
| `siasa-stakeholder-fulfillment-roadmap.md` | Strategie `Step A/B/C`, Phasen `P0–P4` | Abschnitte 2–4 |
| `siasa-next-big-packages-executive-view.md` | Executive `G1–G5`-Einseiter | Abschnitt 2/3 |
| `siasa-planning-audit-and-next-steps.md` | Planungs-Hygiene/Audit | Abschnitt 6 (Aufgabe erfüllt) |
| `siasa-functional-implementation-plan.md` | `AP-F01..F27` Funktionsplan (ausgeführt) | AP-01 (Historie) |
| `siasa-stakeholder-gap-sweep-and-development-sequence.md` | `AP-N01` Gap-Sweep | AP-01/AP-05 (Historie) |
| `siasa-stakeholder-functional-closure-gap-plan.md` | 19-ID Closure-Cluster (erfüllt) | AP-01 (Historie) |
| `siasa-level-3-user-value-flow-plan.md` | L3 User-Value-Flow (großteils erfüllt) | AP-05 (Historie) |
| `siasa-level-4-demo-release-readiness-plan.md` | L4 Release-Readiness (erfüllt/überholt) | AP-04 (Historie) |
| `siasa-initial-implementation-workpackages.md` | Bootstrap-Erstplanung | AP-01 (Historie) |
| `siasa-p0-wp-001-source-access-assessment.md` | Source-Access-Constraints | AP-06 (Constraints übernommen) |
| `siasa-p0-wp-002c-domain-b-source-selection.md` | Domain-B-Source-Selection-Notiz | AP-06 (Historie) |

Weiterhin aktiv (nicht abgelöst): `docs/plans/siasa-capability-fulfillment-matrix.md` als Evidenz-Begleiter
(von `src/siasa/readmodels/release_evidence.py` gelesen).

---

## 7. Pflegeregeln

1. Nach jedem abgeschlossenen Teilarbeitspaket: Status hier aktualisieren, Evidenz/Herkunft ergänzen,
   Capability-Matrix als Evidenz-Begleiter nachziehen.
2. Strategische Priorität (Abschnitt 3) nur überarbeiten, wenn ein Pivot-Auslöser (Abschnitt 5) eintritt.
3. Neue Arbeitspakete: nächste freie `AP-NN` (Ebene 1) bzw. `AP-NN.M` (Ebene 2); IDs nie wiederverwenden.
4. Keine neue Parallel-Planungsgeneration anlegen – dieses Dokument bleibt die einzige Planungsquelle.
5. Bei neuen Begriffen/Konzepten: `docs/glossary.yaml` ergänzen; bei Begriffs-Widersprüchen Glossar als Referenz.
