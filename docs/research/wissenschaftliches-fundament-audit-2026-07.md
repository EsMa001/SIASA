# Wissenschaftliches Fundament-Audit — SIASA (Juli 2026)

Stand: 2026-07-19 · Bezug: Commit `bc54f8f` · Status: **Phase I abgeschlossen als AP-34** — V-1, V-2, V-4, V-5, V-6, V-7 und die Sofort-Hygiene umgesetzt (SwR-109..114); V-3 (Kontroll-Replay-Inputs) bewusst nach AP-30.4 verschoben, siehe §8. Phase II (V-8..V-11) und Phase III (V-12..V-18) offen.

---

## 0. Auftrag und Methode

Auftrag: die technischen und wissenschaftlichen Grundlagen des Projekts kritisch hinterfragen,
alle Auffälligkeiten dokumentieren und konkrete, umsetzbare Verbesserungen erarbeiten.

Methode: Sechs unabhängige, repo-verankerte Analyse-Linsen (Scoring/Aggregation, Statistik,
Validierung, Datenbasis, Zeitdynamik, Epistemik/Governance) mit der Auflage, jede Behauptung
mit Datei:Zeile zu belegen. Die Kernbefunde wurden anschließend **erstverifiziert** — durch
direktes Lesen des Codes und in einem Fall durch ein beweisendes Experiment (§2, A-02).

**Verifikationsstatus-Legende** (an jedem Befund):

| Marke | Bedeutung |
| --- | --- |
| **[E]** | Erstverifiziert: direkt am Code geprüft bzw. experimentell belegt |
| **[A✓]** | Agentenbefund, Beleg stichprobengeprüft |
| **[A]** | Agentenbefund mit Datei:Zeile-Beleg, nicht separat nachgeprüft |

Limitierungen dieses Audits selbst (Ehrlichkeitsgebot): (1) Die geplante adversariale
Zweitprüfung aller Einzelbefunde und die beiden Literatur-Recherche-Linsen fielen einem
API-Rate-Limit zum Opfer; die Kernbefunde wurden stattdessen manuell erstverifiziert, die
Literaturangaben in §6 stammen aus Modellwissen und sind als solches markiert. (2) Das Audit
bewertet den Code-Stand `bc54f8f`; Fixtures und Live-Daten wurden gelesen, aber kein
Live-Lauf durchgeführt.

---

## 1. Gesamturteil in drei Systemdiagnosen

Die Einzelbefunde (§2) verdichten sich zu drei Diagnosen, die zusammen den Zustand des
wissenschaftlichen Fundaments beschreiben:

### D1 — Die Messkette validiert nicht das Modell

Der publizierte `skill_score`, der Sensitivitätsbefund („nur d1_max wirkt") und das
`beats_baseline`-Urteil hängen **nicht am datengetriebenen Modell**, sondern an einer
hartkodierten Konstantentabelle, an synthetischen Fixtures und an einer Metrik-Mechanik,
die die Negativkontrollen nie erreicht (A-01, A-02, A-07, A-08, A-09). Konsequenz:
**Jede bisher berichtete Skill- oder Sensitivitätszahl ist über die Modellgüte nicht
aussagekräftig.** Das Projekt weiß das teilweise (ehrliche Code-Kommentare, calibration_note),
aber die Zahlen zirkulieren in Read-Models und Reports ohne diesen Vorbehalt.

### D2 — Der Live-Pfad hat keine Zeitdimension

Die einzige status-treibende Größe (Anomalie) fällt im Live-Betrieb konstruktionsbedingt auf
0.0, weil Einzel-Snapshots die Mindest-Serienlänge nie erreichen (A-03). Die Statusableitung
ist gedächtnislos (A-17), Zeitreihen-Bausteine existieren, sind aber nicht verdrahtet.
Die beiden Extremstufen sind **beide datenlogistisch, nicht sicherheitspolitisch** getrieben:
S0 = „Daten da, keine Historie → Anomalie 0", S6 = „Daten weg in 2 Kern-Domänen" (A-05).
Konsequenz: **Im gegenwärtigen Datenmodus ist SIASA ein Daten-Logistik-Monitor, kein
Instabilitäts-Frühwarnsystem.** Das ändert sich erst mit echter historischer Tiefe
(AP-13/26/30) — die Backlog-Priorisierung ist insoweit korrekt.

### D3 — Dokumentierte Methodik ≠ wirksame Methodik

Die Governance-Fassade ist vorbildlich gebaut (governed YAML, Rationalen, Referenzen,
owner_authority) — aber: 8 von 10 Konsumenten-Modulen binden Parameter zur Import-Zeit,
womit Overrides und Sweeps wirkungslos sind (A-02); Bayes-, Fusions-, Baseline- und
Multi-Resolution-Module werden berechnet, beeinflussen den Status aber nicht (A-15, A-17,
A-27); Governance-Felder wie `ratification_status` und `dataset_split` werden nie gelesen
(A-19, A-20); Methodik-Etiketten (GUM, SHELF, NATO Admiralty, „Bayes") stehen über deutlich
einfacheren Mechaniken (A-14, A-15, A-18, A-24). Konsequenz: **Der wissenschaftliche
Anspruch besteht in relevanten Teilen auf dem Papier.** Wer die Dokumentation liest, glaubt
an ein reicheres System, als der wirksame Codepfad ist.

---

## 2. Befundkatalog

Sortiert nach Schwere. Jeder Befund: Behauptung → Beleg → Konsequenz.

### Kritisch

**A-01 [E] Skill- und Sensitivitätskette misst eine Konstantentabelle, nicht das Modell.**
`historical_replay.py:45` definiert `_DOMAIN_ANOMALY_SCORES = {"A": 0.7, "B": 0.3, "C": 0.2,
"D": 0.1, "E": 0.2}`; `:168` speist diese Konstante — identisch für jedes Land und jedes
Ereignis — als `anomaly_score` in `derive_domain_status`, dessen Ergebnis über `:285` zum
`replayed_status` und damit zur alleinigen Grundlage von `skill_score` und OAT-Sensitivität
wird. Der Code-Kommentar (`:40-44`) ist ehrlich („keeps this constant until AP-26 …
avoids collapsing the thin synthetic fixtures to S0"), aber die daraus erzeugten Kennzahlen
tragen den Vorbehalt nicht. *Konsequenz:* Der dokumentierte Sensitivitätsbefund
(„d1_max-Einfluss 0.4286") ist ein Artefakt: der Sweep hat effektiv einen einzigen
Freiheitsgrad — ob die Konstante 0.7 über oder unter der d1/d2-Kante liegt.

**A-02 [E, experimentell bewiesen] Governance-Verdrahtung: 8 von 10 Modulen binden Parameter
zur Import-Zeit — Overrides und Sweeps sind wirkungslos.**
Zensus per Grep: `anomaly.py:27,30`, `probabilistic.py:19-21`, `cross_domain_fusion.py:41-44`,
`uncertainty_propagation.py:47-48` (im Funktionskörper, aber siehe unten), `info_epidemiology.py:13`,
`backtesting.py:72`, `historical_replay.py:23-24`, `skill_metrics.py:34` weisen Modul-Konstanten
zu; nur `domain_status.py:27` und `data_sufficiency.py:46-50` rufen die Getter pro Aufruf.
Experiment (2026-07-19): unter `override_thresholds({('anomaly','upper_bound'): 99.0})` liefert
der Loader 99.0, `anomaly.ANOMALY_UPPER_BOUND` bleibt 1.5. *Konsequenz:* (1) Der
Sensitivitäts-Sweep konnte für alle importgebundenen Familien **mechanisch nur 0.0 messen** —
exakt die einzige korrekt verdrahtete Familie (domain_status) zeigte Einfluss. (2) Tests mit
`override_thresholds` prüfen für 8 Familien nicht das, was Produktion tut. (3) Governed
YAML-Änderungen wirken erst nach Prozess-Neustart.

**A-03 [E] Die Live-Anomalie degeneriert konstruktionsbedingt auf 0.0 — das System meldet
im Live-Betrieb fast immer S0.**
`anomaly.py:71` verwirft jede Signalserie mit weniger als `min_series_points = 4`
Beobachtungen; ein Live-Bundle trägt typischerweise 1 Beobachtung je Signal; `:83-84` liefert
dann 0.0. Der Docstring (`:10-17`) benennt das selbst („the anomaly honestly reads ~0 there").
*Konsequenz:* Alle nachgelagerten Schwellen, Bayes-Schichten und Fusionsgewichte operieren im
Live-Betrieb auf einer Konstanten. Ohne AP-13/26/30 (Archiv, PIT-Fenster, Backfill) existiert
keine wirksame Analytik — die Backlog-Reihenfolge ist deshalb richtig, aber der Zustand muss
in jeder Statusanzeige sichtbar sein (derzeit erscheint schlicht „S0", was wie „ruhig" liest).

**A-04 [E] Länder-Vergleichbarkeit strukturell verletzt: die S-Stufe hängt von der Anzahl
aktiver Domänen ab.**
`multi_domain_status.py:34-47` ist eine reine Abzählregel (`len(strong) >= 2 → S4/S3`,
`len(notable) >= 2 → S3` …). Ein Land mit nur einer aktiven Domäne kann strukturell maximal
S2 erreichen (`len(very_strong)==1`), egal wie kritisch die Lage ist.
`live_runtime.py:398` governt `"TWN": ["A"]` — Taiwan ist damit auf S2 gedeckelt, während
`["A","B","D"]`-Länder S4 erreichen können. *Konsequenz:* Die Länder-Rangfolge wird von
Quellen-/Domänenverfügbarkeit getrieben, nicht von Instabilität — genau die Verzerrung, die
das OECD/JRC-Handbuch und die INFORM-Methodik durch Normierung ausschließen. Dieser Punkt
fehlt im governance_record vollständig.

**A-05 [E] S6 (höchste Stufe) wird durch Datenausfall ausgelöst, nicht durch Instabilität.**
`multi_domain_status.py:29-31`: sind ≥2 Kern-Domänen (A/B/D) auf D0 (= unzureichende Daten),
wird sofort S6 zurückgegeben. Zusammen mit A-03 gilt: **beide Extreme der Skala messen
Datenlogistik** — S0 = „Daten da, keine Historie", S6 = „Daten weg". Ein routinemäßiger
Doppel-Adapterausfall erzeugte die höchste Alarmstufe. *Konsequenz:* Die Skala vermengt
zwei orthogonale Größen (Bedrohungslage, Datenlage); ein „data blackout"-Zustand gehört
getrennt ausgewiesen, mit Eskalation nur bei zuvor erhöhter Baseline.

**A-06 [E] Die einzige kuratierte Konfliktquelle (UCDP) wird geladen, aber nie konsumiert —
Domäne B misst Medienaufmerksamkeit.**
Der UCDP-Adapter emittiert `armed_conflict_events`, `battle_deaths_best`,
`state_based_events` (`ucdp.py:482ff`); ein Grep über `src/` findet **keinen einzigen
Konsumenten** dieser Signalschlüssel. `features/domain_b.py:19-23` liest ausschließlich
GDELT-Zählungen (`conflict_event_count`, `protest_event_count`, `violent_event_count`) und
den GDACS-Alarm. *Konsequenz:* Die Sicherheits-Domäne beruht vollständig auf einem
Medien-Aufmerksamkeits-Proxy mit dokumentierten Verzerrungen (§6), während die kuratierte
Bodenwahrheit inkl. Kampftoten ungenutzt im Datenstrom liegt. (Ironie am Rande: der
UCDP-Adapter wurde heute mit erheblichem Aufwand funktionsfähig gemacht — AP-06.4.)

**A-07 [E] Fehlalarmrate und beats_baseline laufen strukturell leer: die Negativkontrollen
erreichen die Metrik nie.**
`historical_replay.py:283-284` überspringt jeden Fall ohne Replay-Input;
`validation_replay_inputs.yaml` enthält 35 case_ids, davon **0 Negative** (Grep). Damit ist
`negative_total = 0`, `false_alarm_rate = 0.0` per Division-Guard (`skill_metrics.py:109`),
und `beats_baseline` vergleicht 0.0 mit 0.0. *Konsequenz:* Das gesamte AP-27/28-Konstrukt
(matched pairs, S0-Kontrollen) ist in der wirksamen Metrik nicht angekommen; die
Fehlalarm-Behauptung ist eine Leerstelle.

### Hoch

**A-08 [E] Zirkuläre Labels sind bekannt, aber nicht blockierend.**
`cases.py:135-140` erkennt `historical_observed_status == expected_status` als
`circular_label_case_ids`; `:152` schließt sie **aus `is_valid` aus**. Alle realen
Onset-Positivfälle tragen S3==S3 (`validation_reference_cases.yaml:699f`, AZE/NER/AFG/MMR/SYR
analog). *Konsequenz:* Der Anti-Zirkularitäts-Validator existiert, beißt aber nicht — das
Soll-Label ist mit dem Beobachtungs-Label identisch, Status-Match misst Selbstübereinstimmung.

**A-09 [E] Die No-Skill-Baseline ist ein Strohmann; die berechnete Brier-Baseline wird im
Urteil nicht verwendet.**
`skill_metrics.py:37` setzt „immer S3" als Baseline — sie alarmiert per Konstruktion auf
jedem Kontrollfall (FAR 1.0) und ist damit trivial schlagbar. `baseline_brier_score` wird
berechnet (`:175`), fließt aber nicht in `beats_baseline` (`:153-157`) ein. Es gibt keine
Basisraten-/Klimatologie-Baseline, obwohl Konflikt-Onset selten ist. *Konsequenz:* „schlägt
die Baseline" ist mit dieser Konstruktion keine wissenschaftliche Aussage.

**A-10 [A✓] n=8 Paare ohne Unsicherheitsquantifizierung.**
`compute_skill_metrics` liefert reine Punktschätzer; kein Konfidenzintervall, kein Test
(Grep: `confidence|bootstrap|p_value` in `src/siasa/validation/` = 0). Bei 8 Negativen hat
eine beobachtete FAR von 0/8 ein Wilson-95%-Intervall bis ≈ 0.32. *Konsequenz:* Selbst nach
Reparatur von A-07 wäre jede Skill-Aussage ohne Intervall irreführend.

**A-11 [E] Der z-Score verletzt die eigene SPC-Referenz: Testpunkt in der eigenen Baseline,
Populations-σ, Sättigung.**
`anomaly.py:34-37` (Varianz ÷ n, inkl. Testpunkt), `:73-74` (z-Score des letzten Werts gegen
das ihn enthaltende Fenster). Max |z| ≈ √(n−1), bei n=4 also 1.73, gegen Cutpoints
0.2/0.5/1.0 und Cap 1.5 → nahezu binäres Verhalten (Docstring `:14-17` räumt das ein).
SPC (die zitierte Referenz) verlangt die Phase-I/Phase-II-Trennung: Kontrollgrenzen aus
einer Baseline **ohne** den Prüfpunkt. *Konsequenz:* Abgestufte D2/D3-Bänder sind auf kurzen
Fenstern kaum erreichbar; der Schätzer ist nach unten verzerrt und bei kleinem n dominiert
Rauschen.

**A-12 [A✓] Coverage ist strukturell konstant 1.0 — „coverage-weighted" ist ungewichtet,
der 0.6-Floor greift nie.**
Alle Adapter setzen `expected_source_count: 1` (u. a. `gdelt_events.py:202`, `ucdp.py:492`,
`world_bank.py:149`); `features/base.py:103` ergibt damit `coverage = min(1.0, n/1) = 1.0`.
*Konsequenz:* Quellen-Untererfassung ist nicht beobachtbar; die Suffizienz-Schwelle
`minimum_coverage: 0.6` ist toter Parameter; die Anomalie-Gewichtung ist ein einfacher
Mittelwert.

**A-13 [A] Freshness-Gate ist Selbstzertifizierung.**
Adapter setzen `freshness_horizon_hours` gleich ihrer eigenen `freshness_hours`
(z. B. `world_bank.py:150-151`, beide 8760); die governte `freshness_config.yaml` wird nur
als Fallback konsultiert. Die Bedingung `freshness_hours > horizon` ist damit per
Konstruktion unerfüllbar. *Konsequenz:* Veraltete Daten können das Suffizienz-Gate nicht
reißen; „Frische" ist als Qualitätsdimension wirkungslos.

**A-14 [A✓] Die „GUM"-Unsicherheitsfortpflanzung ist pseudo-GUM.**
`uncertainty_propagation.py:46-70`: (1) Die RSS-Quadratur setzt Unabhängigkeit voraus —
Korrelationsterme fehlen, obwohl Quellen einer Domäne korreliert sind. (2) Die
Eingangs-„Unsicherheit" ist `1 − coverage` (wegen A-12 fast immer 0), keine
Standardabweichung. (3) Drei Stage-Noise-Terme sind deterministische Vielfache derselben
Größe `source_mean` und werden als unabhängige Varianzen addiert. *Konsequenz:* Die
ausgewiesenen Konfidenzintervalle haben keine belastbare probabilistische Interpretation.

**A-15 [E] Die „Bayes"-Schicht ist ein distanzbasierter Soft-Klassifikator ohne Lernen,
ihr MAP ist nicht statusbildend, und `transition_probability` ist erfundene Mathematik.**
`probabilistic.py:38` setzt den Prior bei jedem Aufruf uniform (kein sequentielles Update);
centers/σ sind gesetzt, nicht geschätzt; der Orchestrator legt die Posteriors nur in Dicts ab
(`orchestrator.py:300,313`), der Status kommt ausschließlich aus der Abzählregel.
Regel-Cutpoints (0.2/0.5/1.0) und Bayes-Zentren (0.1/0.35/0.75) implizieren **verschiedene
Klassengrenzen** (MAP-Grenzen = Mittelpunkte der Zentren: 0.05/0.225/0.55/0.875) — dieselbe
Anomalie kann in beiden Subsystemen verschiedenen Status ergeben. `transition_probability`
(`:67-74`) nutzt `exp(−distance²)` ohne jede empirische Übergangsmatrix und wird nirgends im
Produktionspfad aufgerufen. *Konsequenz:* Das Etikett „Bayesian estimation" überzeichnet;
zwei parallel dokumentierte Statuslogiken können sich widersprechen.

**A-16 [E/A] `lead_time` misst Datenankunft und Fensterwahl, nicht Prognosefähigkeit.**
`skill_metrics.py:55-62,98-101`: erster Nicht-S0-Tag relativ zum Onset; gemittelt **nur über
detektierte Positive** (Selektionseffekt); Alarm = „≠ S0" (S1 zählt voll). In den Fixtures
liegen die A/B-Signale auf dem Onset-Tag selbst (`validation_replay_inputs.yaml`, UKR:
2022-02-24), Vorlauf entsteht durch den handgewählten Fensterbeginn. *Konsequenz:* Positive
Lead-Times sind derzeit kein Beleg für Frühwarnung; Nowcast und Forecast sind unmarkiert
vermengt.

**A-17 [A✓] Zeitdynamik ist nicht modelliert; vorhandene Zeitreihen-Bausteine sind verwaist.**
Statusableitung ist gedächtnislos (`domain_status.py:32-39`, `multi_domain_status.py:34-47`);
kein Slope/Momentum/Persistenz/Hysterese; jeder Replay-Tag wird isoliert gerechnet
(`historical_replay.py:258-262`). `MultiResolutionBuilder` (7d/30d-Rolling) und
`compute_combined_baseline` (30/90/365) existieren, werden aber im Produktionspfad nie
aufgerufen (nur Tests/GUI-Doku). `expected_trajectory` wird geladen und durchgereicht, aber
nie bewertet (`cases.py:156-172`). *Konsequenz:* Schleichende Eskalation ist strukturell
unsichtbar (die mitlaufende Baseline absorbiert sie), Status kann tagesscharf flackern, und
das wertvollste Label (die Trajektorie) bleibt ungenutzt.

**A-18 [A✓] NATO-Admiralty ist als zweiachsige Doktrin nicht implementiert.**
`cross_domain_fusion.py:133-139` vergibt einen einzigen Skalar nach Datensuffizienz
(1.0/0.6/0.2). Die Doktrin verlangt zwei unabhängige Achsen: Quellen-Zuverlässigkeit (A–F)
und Informations-Glaubwürdigkeit (1–6). *Konsequenz:* Eine zuverlässige Quelle mit
unplausibler Einzelinformation ist vom Gegenteil nicht unterscheidbar; das Etikett in der
Doku verspricht mehr als der Mechanismus.

**A-19 [E] `dataset_split` (tuning/holdout) ist dekorativ.**
Definiert und validiert in `cases.py`, aber von keiner Codestelle genutzt, um Tuning auf
den Tuning-Split zu beschränken (Grep über `src/`, `scripts/`). *Konsequenz:* Die
Schwellen-Kalibrierung (AP-24) und jede Evaluation laufen auf derselben Menge — die formale
Voraussetzung für Overfitting-freie Skill-Aussagen fehlt.

**A-20 [A✓] `ratification_status` ist tote Governance.**
Nie im Code gelesen (Grep in `src/` = 0 Treffer); 16 von 49 Fällen tragen das Feld, alle
uniform `research_verified`. *Konsequenz:* Der Ratifizierungs-Workflow existiert nur als
Text; die Metrik unterscheidet nicht zwischen ratifizierten und unratifizierten Fällen.

### Mittel

**A-21 [A✓] Keine Populations-/Medien-Normalisierung; GDELT roh.**
Event-Zeilen zählen +1.0 (`gdelt_events.py:181-185`), keine Gewichtung nach
NumMentions/NumArticles, keine Deduplizierung, kein Bezug auf Landes-Medienvolumen oder
Bevölkerung (Grep `per_capita|population|media_density` = 0 in features/scoring). Domäne A
nutzt rohes `article_count`. *Konsequenz:* Cross-Country-Vergleiche spiegeln Medien-Dichte;
das Selbst-z-Scoring (der nominelle Ausgleich) ist wegen A-03 im Live-Betrieb inert.

**A-22 [A] Domäne A ist de facto Single-Source.** `wiki_pageview_count` wird emittiert
(`wikipedia_pageviews.py:159`), aber von `features/domain_a.py` nicht gelesen. Der Katalog
zählt 2 Quellen, wirksam ist eine.

**A-23 [A] Brier-„Wahrscheinlichkeit" ist eine Ordinal-Transformation.**
`_event_probability = Ordinal/6` (`skill_metrics.py:41-43`) — S3 ≙ 0.5 ist Setzung, keine
Kalibrierung (Docstring markiert es als Platzhalter). Der Brier-Wert ist damit keine
Aussage über probabilistische Güte.

**A-24 [A] Etiketten-Inflation: „per SHELF" für einen Band-Mittelpunkt.**
`scoring_thresholds.yaml:85` deklariert die D3-Zentrums-Setzung (0.65→0.75 =
Bandmitte) als „per SHELF"; SHELF ist ein strukturiertes Elicitation-Protokoll, kein
Intervall-Mittelwert. Gleiches Muster wie A-14/A-15/A-18.

**A-25 [A] Provenance-Vollständigkeits-Ratio ist tautologisch.**
`historical_replay.py:67-68` prüft nur Nicht-Leere zweier Felder, die `:146-147` automatisch
aus denselben Records ableitet — für jeden Fall mit Records zwangsläufig erfüllt; speist
dennoch das Evidenz-Tier.

**A-26 [A] Subnationale Auflösung wird verworfen.** GDELT/UCDP liefern Koordinaten; die
Aggregation ist ausschließlich ISO3-Länderebene. Für große Länder (IND, NGA, SDN) mittelt
das regionale Krisen ins Landesrauschen.

**A-27 [A✓] Zwei widersprüchliche Aggregationsphilosophien parallel.**
Headline: nicht-kompensatorische Abzählregel; parallel eine voll kompensatorische
arithmetische Fusion (`fused_score`, `cross_domain_fusion.py:186`), die nicht statusbildend
ist. `scoring_thresholds.yaml:69-73` empfiehlt `geometric_mean_equal_weights` und markiert
die Familie ehrlich als `wired_to_config: false`. Die GUI beschreibt zudem den ungenutzten
Baseline-Pfad als aktive Methodik.

**A-28 [A] Domänen-Label-Inkonsistenz.** Kommentare in `freshness_config.yaml:13-17`
ordnen A/B/D anders zu als `domains.yaml` und der Code — reine Doku-Hygiene, aber
verwirrend für jede Kalibrierungsdiskussion.

---

## 3. Was das Projekt richtig macht

Der Vollständigkeit halber — diese Punkte sind echt und tragen:

1. **Selbstdiagnose-Ehrlichkeit im Kleinen.** Docstrings benennen Grenzen offen
   (Anomalie-Degeneration, Konstanten-Platzhalter, Fixture-Vorbehalt in der
   calibration_note). Das Audit konnte viele Befunde *aus den eigenen Kommentaren des
   Projekts* belegen — das ist ungewöhnlich und wertvoll.
2. **Governance-Struktur.** `scoring_thresholds.yaml` mit current/recommended/rationale/
   reference je Familie ist der richtige Rahmen; mehrere Empfehlungen darin sind fachlich
   korrekt (Geomittel, σ-Vielfache, ≥20 Punkte) — sie sind nur nicht umgesetzt.
3. **V-Modell-Traceability** ist real und maschinell geprüft (102 SwR, 17 Slices, Closure-
   Tests) — die heutige UCDP-Episode zeigte zugleich die Grenze: Existenz einer Anforderung
   garantiert keine wirksame Verifikation (Mock-Tests ließen einen nie funktionsfähigen
   Adapter passieren).
4. **Matched-Pairs-Design und PIT-Monotonie** sind konzeptionell die richtigen Instrumente;
   sie scheitern derzeit an der Zuführung (A-07, A-08), nicht an der Idee.
5. **Die Backlog-Priorisierung** (AP-13/26/30 vor Modell-Feinheiten) adressiert D2 korrekt.

---

## 4. Verbesserungs-Roadmap

Leitprinzip: **Erst die Messkette reparieren, dann die Substanz** — jede Substanzänderung,
die mit der heutigen Messkette „validiert" würde, erzeugte nur neue Scheinzahlen.
Efforts: S ≤ 1 Tag · M = 1–3 Tage · L = 1–2 Wochen · XL > 2 Wochen.
SwR-IDs sind **Vorschläge**; Vergabe gegen das Reservierungsregister im Masterplan prüfen
(nächste freie ID: SwR-109).

### Phase I — Messkette reparieren (Voraussetzung für alles Weitere)

| # | Maßnahme | Behebt | Aufwand |
| --- | --- | --- | --- |
| **V-1** | **Per-Call-Bindung aller governed Parameter.** Die 8 importbindenden Module auf Getter-Aufruf pro Funktionsaufruf umstellen (Muster: `domain_status.py`). Regressionstest: parametrisiert über `get_all_scoring_thresholds()` beweisen, dass `override_thresholds` **jede** Familie wirksam ändert. | A-02 | M |
| **V-2** | **Sensitivitäts-Harness ehrlich machen.** Probe-Grid automatisch aus allen governed Familien generieren (statt 5 handgepflegter Einträge); Report kennzeichnet hart „fixture-bound, nicht modellaussagekräftig", solange A-01 besteht; nach V-1+V-4 Re-Run. | A-01, A-02 | S–M |
| **V-3** | **Negativkontrollen in die Metrik bringen.** Replay-Inputs für die 8 S0-Kontrollen erzeugen (reale, ruhige Zeitfenster); Guard: `compute_skill_metrics` schlägt fehl oder markiert das Ergebnis, wenn `negative_total == 0`. | A-07 | M |
| **V-4** | **Zirkularität blockierend machen.** `circular_label_case_ids` in `is_valid` aufnehmen; `historical_observed_status` muss aus einer vom Soll-Label unabhängigen Quelle stammen (dokumentierter Beobachtungspfad je Fall). | A-08 | S–M |
| **V-5** | **Ehrliche Baseline + Unsicherheit.** Klimatologie-Baseline (beobachtete Onset-Rate des Sets; perspektivisch externe Basisrate), Brier Skill Score `BSS = 1 − B/B_ref` als `beats_baseline`-Kriterium; Wilson-Intervalle für Recall/FAR; n im Report immer neben der Zahl. | A-09, A-10, A-23 | M |
| **V-6** | **`dataset_split` durchsetzen.** Sensitivity/Kalibrierung filtert auf `tuning`, Skill-Report ausschließlich `holdout`; Test erzwingt die Trennung. | A-19 | S |
| **V-7** | **Lead-Time sauber definieren.** Nur Alarme *vor* Onset zählen; Nicht-Detektionen als zensiert ausweisen statt stillschweigend auszuschließen; Alarm-Schwelle explizit governen (z. B. ≥ S2 statt ≠ S0); Nowcast/Forecast getrennt reporten. | A-16 | S–M |

*Ergebnis von Phase I:* Kennzahlen, denen man trauen kann — auch wenn sie zunächst schlechter
aussehen werden als die heutigen.

### Phase II — Der Live-Pfad bekommt eine Zeitdimension (Träger: AP-13/26/30)

| # | Maßnahme | Behebt | Aufwand |
| --- | --- | --- | --- |
| **V-8** | **SPC-konforme Anomalie.** Baseline ohne Prüfpunkt (Leave-one-out bzw. Phase-I-Fenster), Stichproben-σ (n−1), `min_series_points ≥ 20` (steht bereits als Empfehlung im governance_record), Cutpoints danach in σ-Vielfachen (1/2/3) rekalibrieren; ALGO-ANOM-01 in den Replay-Pfad verdrahten (löst A-01 substanziell ab). | A-01, A-11 | M–L |
| **V-9** | **Schleichende Eskalation sichtbar machen.** EWMA oder CUSUM je Signal (beides bereits als Referenz im governance_record); `MultiResolutionBuilder` (7d/30d) in den Produktionspfad verdrahten oder entfernen. | A-17 | M–L |
| **V-10** | **Persistenz und Hysterese.** n-von-m-Bestätigung vor Eskalation, De-Eskalations-Verzögerung; `expected_trajectory` in der Validierung tatsächlich bewerten (Trajektorien-Match statt nur Endstatus). | A-17 | M |
| **V-11** | **Datenlage von Bedrohungslage trennen.** Eigener `data_blackout`-Zustand statt S6-aus-D0; S-Stufe erhält ein sichtbares Konfidenz-/Datenlage-Attribut; „S0 mangels Historie" wird als „unbewertet" angezeigt, nicht als „ruhig". | A-03, A-05 | M |

### Phase III — Substanz (nach Phase I+II messbar)

| # | Maßnahme | Behebt | Aufwand |
| --- | --- | --- | --- |
| **V-12** | **UCDP konsumieren.** `domain_b.py` liest `armed_conflict_events`/`battle_deaths_best`/`state_based_events`; GDELT wird als Aufmerksamkeits-Signal, UCDP als Intensitäts-Signal deklariert (getrennte Feature-Keys, beide im Feature-Vektor). | A-06 | M |
| **V-13** | **Normalisierung.** GDELT: log-Transformation + Anteil am Landes-Gesamtvolumen statt Rohzählung; UCDP: pro Kopf bzw. log; `expected_source_count` je (Domäne, Signal) aus der Quellen-Registry statt hart 1; Freshness-Horizont aus `freshness_config.yaml` erzwingen statt Selbstzertifikat. | A-12, A-13, A-21 | M–L |
| **V-14** | **Aggregation nach INFORM-Vorbild.** Kontinuierliche Domain-Severity in [0,1]; gleichgewichtetes geometrisches Mittel über die aktiven Domänen (bereits empfohlene Familie `multi_domain_aggregation_s0_s6`); Normierung auf Domänenzahl, damit A-04 fällt; Round-up-Diskretisierung auf S-Stufen. | A-04, A-27 | L |
| **V-15** | **Bayes-Schicht: verdrahten oder entfernen.** Entweder: sequentielles Update (Vortages-Posterior als Prior), σ aus Backfill kalibriert, MAP statusbildend, Grenzen mit Cutpoints konsistent — oder: Modul als deskriptiv labeln und `transition_probability` löschen, bis eine empirische Übergangsmatrix aus dem Backfill existiert. | A-15 | M–XL (je nach Weg) |
| **V-16** | **Unsicherheit ehrlich.** Pseudo-GUM ersetzen: empirische Streuung aus dem Backfill (Bootstrap über Quellen/Fenster) statt deterministischer Stage-Noise; bis dahin CI-Ausgabe entfernen oder als „heuristisch" labeln. | A-14 | M–L |
| **V-17** | **Admiralty zweiachsig.** Quellen-Zuverlässigkeit aus der Quellen-Registry (statisch, governed), Informations-Glaubwürdigkeit aus Korroboration über unabhängige Quellen (dynamisch); Fusionsgewicht = f(beide Achsen). | A-18 | L |
| **V-18** | **Subnationale Option prüfen.** Koordinaten aus GDELT/UCDP in ADM1-Buckets aggregieren (nur für große Pilotländer); kein Muss für den MVP, aber die Datenlage gibt es her. | A-26 | XL |

### Sofort-Hygiene (unabhängig, jeweils S)

- `ratification_status` entweder in die Validierung einlesen (Gate) oder aus den YAMLs
  entfernen (A-20).
- „per SHELF"-Etikett in `scoring_thresholds.yaml:85` durch ehrliche Formulierung ersetzen
  („Bandmitte als Interim, Elicitation ausstehend") (A-24).
- GUI-Methodikseiten: nicht verdrahtete Pfade (Baselines, Fusion, Bayes) als „berechnet,
  nicht statusbildend" kennzeichnen (A-27, D3).
- Freshness-Kommentar-Labels in `freshness_config.yaml` an `domains.yaml` angleichen (A-28).
- Wikipedia-Pageviews konsumieren oder Quelle aus dem Domäne-A-Katalog streichen (A-22).
- Skill-/Sensitivitäts-Ausgaben mit hartem Banner versehen: „fixture-bound; nicht
  modellaussagekräftig", bis V-1..V-5 umgesetzt sind (D1).

---

## 5. Vorgeschlagene Reihenfolge und Verankerung

1. **Sofort-Hygiene** (ein Arbeitstag, keine Designentscheide) — beseitigt die
   Etiketten-/Doku-Diskrepanzen, die D3 ausmachen.
2. **Phase I komplett** (V-1..V-7) — danach erstmals belastbare Zahlen; das ist die
   wissenschaftliche Mindestbedingung, bevor irgendeine Modelländerung „besser/schlechter"
   genannt werden darf.
3. **Phase II mit AP-13/26/30 verschränken** — die Backfill-Arbeiten sind ohnehin der
   kritische Pfad; V-8..V-11 definieren, *was* auf den neuen Zeitreihen gerechnet wird.
4. **Phase III** nach Owner-Priorität; V-12 (UCDP konsumieren) und V-13 (Normalisierung)
   zuerst, weil sie die Konstruktvalidität von Domäne B/A direkt heben.

Jede Maßnahme braucht nach Projektregel eine SwR (ab SwR-109, Reservierungsregister
beachten) und den Count-Sync-Ritus. Vorschlag zur Bündelung: **AP-34 „Messketten-Integrität"**
(Phase I + Hygiene), **AP-35 „Zeitdynamik"** (Phase II, als TAPs unter AP-26/30 einhängbar),
**AP-36 „Konstruktvalidität Datenbasis"** (V-12/V-13), **AP-37 „Aggregation & Evidenz"**
(V-14..V-17).

---

## 6. Wissenschaftlicher Kontext (Feldstandard)

**Herkunftsvorbehalt:** Dieser Abschnitt stammt aus Modellwissen (Stand ≈ Anfang 2026); die
geplante Web-Verifikation fiel dem Rate-Limit zum Opfer und kann nachgeholt werden. Die
Aussagen sind als Orientierung belastbar, Zitate/URLs wären vor formaler Übernahme zu prüfen.

- **ViEWS** (Uppsala/PRIO): der akademische Referenzstandard — probabilistische
  Konfliktprognosen auf Länder- *und* Rasterzellen-Ebene (pgm), Ensemble-Modelle,
  ausgewiesene Prognosehorizonte (1–36 Monate), seit der Prediction Challenge 2023/24 mit
  expliziter Unsicherheitsquantifizierung (u. a. CRPS als Metrik). Lehre für SIASA: Skill
  wird dort *immer* gegen Basisraten-Benchmarks und mit Verteilungen, nie als einzelner
  Punktwert berichtet.
- **Early Warning Project** (USHMM): arbeitet bewusst mit Basisraten (~1–4 %/Jahr für
  Massengewalt-Onset) und kommuniziert Ränge/Wahrscheinlichkeiten statt Statusstufen —
  das direkte Gegenmodell zum Strohmann-Baseline-Problem (A-09).
- **PITF** (Political Instability Task Force): historisch der Beleg, dass mit wenigen
  strukturellen Variablen und sauberem Out-of-Sample-Design AUCs um 0.8 für
  Instabilitäts-Onset erreichbar sind — aber nur mit großen Fallzahlen über Jahrzehnte;
  n=8 erlaubt solche Aussagen prinzipiell nicht (A-10).
- **ACLED CAST**: praxisorientierte Event-Count-Prognosen mit dokumentierter
  Backtest-Methodik; relevant als Vorbild für die Trennung Nowcast/Forecast (A-16).
- **Event-Daten-Kritik**: GDELT misst Medienberichterstattung, nicht Ereignisse — die
  dokumentierten Probleme (Duplikate, Precision, Medien-Dichte-Bias, Sprachraum-Bias) sind
  seit Ward et al. 2013 und Hammond & Weidmann 2014 Standardwissen; UCDP GED vs. ACLED
  (Eck 2012; Raleigh et al.) zeigt systematische Abdeckungsunterschiede je nach
  Quellenbasis. Konsequenz für SIASA: GDELT als *Aufmerksamkeits*-Signal labeln (V-12),
  Zählungen normalisieren (V-13), UCDP als Intensitäts-Anker nutzen.
- **Verifikationspraxis** (WMO/Meteorologie): Brier nur mit kalibrierten
  Wahrscheinlichkeiten, Skill nur relativ zu Klimatologie/Persistenz, Intervalle statt
  Punktwerte — deckungsgleich mit Phase I dieser Roadmap.

Einordnung: SIASA will bewusst **kein** ML-Großprojekt sein, sondern ein regelbasiertes,
governancegeführtes Monitoring. Das ist legitim — der Feldstandard verlangt dann aber
mindestens: ehrliche Basisraten-Benchmarks, Out-of-Sample-Disziplin, Unsicherheitsintervalle
und Konstruktvalidität der Eingangssignale. Genau das adressieren Phase I und V-12/V-13.

---

## 7. Anhang: Aufklärung des Sensitivitätsbefunds

Der dokumentierte Befund „nur `d1_max` hat Einfluss (0.4286), alles andere 0.0" hat drei
gestapelte mechanische Ursachen und ist **keine Aussage über das Modell**:

1. **Abdeckung:** Der Sweep prüft nur 5 der ~20 governed Parameter
   (`threshold_sensitivity.py:40-46`).
2. **Verdrahtung:** Von den geprüften Familien ist nur `domain_status` pro Aufruf gebunden;
   `anomaly.*` ist importgebunden — Overrides erreichen den Code nie (A-02, experimentell
   bewiesen). Ergebnis 0.0 ist dort zwangsläufig.
3. **Zielmetrik:** `skill_score` hängt am Replay-Status, der aus der Konstantentabelle
   `_DOMAIN_ANOMALY_SCORES` stammt (A-01). Der einzige wirksame Freiheitsgrad ist, ob die
   Konstante A=0.7 die d1/d2-Kante kreuzt — daher exakt ein Parameter mit Einfluss.

Erst nach V-1 (Verdrahtung), V-2 (Vollabdeckung) und V-8 (echte Anomalie im Replay) misst
die Sensitivitätsanalyse das, was ihr Name verspricht.

### Nachtrag 2026-07-19 — Re-Run nach Umsetzung von V-1 und V-2 (AP-34.2/34.3)

V-1 (Per-Call-Auflösung, SwR-109) und V-2 (voll abgeleitetes Probe-Grid + validity_caveat,
SwR-110/ALGO-SENS-01) sind umgesetzt. Der Re-Run über **38 statt 5** Sonden ergibt:

| Parameter | Einfluss | vorher |
| --- | --- | --- |
| `data_sufficiency.minimum_coverage` | **0.4286** | nie gesweept |
| `skill_validation_metrics.detection_weight` | **0.4286** | importgebunden + nie gesweept |
| `domain_status.d1_max` | 0.3600 | 0.4286 (einziger Treffer) |
| `skill_validation_metrics.domain_match_weight` | 0.3315 | importgebunden + nie gesweept |
| übrige 34 Parameter | 0.0000 | überwiegend mechanisch erzwungen |

Interpretation: Das alte Bild „nur d1_max wirkt" ist **widerlegt** — es war ein Abdeckungs- und
Verdrahtungsartefakt (A-02). Die verbleibenden Nullen sind jetzt *ehrliche* Nullen: sie bestätigen
empirisch, dass Bayes-, Fusions-, Unsicherheits- und Anomalie-Familien auf diesen Fixtures nicht
outcome-wirksam sind (konsistent mit A-01, A-03, A-15, A-27). Zwei der vier wirksamen Parameter
sind Gewichte der Metrik selbst (Meta-Sensitivität) — auch das ein ehrlicher Befund über die
Messkette. Alle Werte bleiben per `validity_caveat` als **fixture-bound** markiert, bis V-8/AP-30
echte Zeitreihen in den Replay-Pfad bringen.

---

## 8. Abschluss Phase I (2026-07-19) — was sich faktisch geändert hat

Phase I ist als **AP-34** umgesetzt (Commits `dbb1652`, `d36ae90`, Folge-Commit für V-5).
Sieben der acht Maßnahmen sind erledigt; eine ist bewusst verschoben.

| Maßnahme | Umsetzung | SwR |
| --- | --- | --- |
| Sofort-Hygiene | SHELF-Etikett ehrlich, Domänen-Labels an `domains.yaml` angeglichen, GUI kennzeichnet Bayes/Fusion/Baselines als „berechnet, nicht statusbildend"; die faktisch falsche Fusions-Beschreibung (Gewichte folgen Suffizienz, nicht Severity) korrigiert | — |
| **V-1** Verdrahtung | 7 Module auf Per-Call-Auflösung; Verbots-Wächter gegen Rückfall; 13 Tests beweisen Wirksamkeit je Familie | SwR-109 |
| **V-2** Sensitivität | Grid aus voller Config (38 statt 5), `not_swept` mit Grund, hartes `validity_caveat` | SwR-110 |
| **V-4** Zirkularität | onset-datierte Positive mit identischen Labels ohne `observation_basis` ⇒ `is_valid: false`; `ratification_status` erstmals maschinell gezählt | SwR-111 |
| **V-6** Split | Holdout aus jeder Kalibrierung ausgeschlossen; Skill je Split; `evaluation_valid` je Sektion; **Kuration v3** (stratifizierter Paar-Split) | SwR-112 |
| **V-7** Lead-Time | governte Alarm-Schwelle; Vorlauf nur für Vor-Onset-Alarme; Nowcast/Miss/undatierbar getrennt gezählt | SwR-113 |
| **V-5** Baseline | Klimatologie-Referenz (Brier = p(1−p)) statt Strohmann; **BSS** als Kriterium in `beats_baseline`; Wilson-95%-Intervalle neben jeder Rate, `None` genau dann, wenn die Rate undefiniert ist | SwR-114 |
| **V-3** Kontroll-Inputs | **verschoben → AP-30.4** (Begründung unten) | — |

### Was Phase I *nicht* geleistet hat — und nicht leisten sollte

Die Messkette lügt nicht mehr; sie ist deswegen aber nicht aussagekräftiger geworden. Der
`validity_caveat` bleibt auf jedem Sensitivitätsreport, die Holdout-Sektion bleibt
`evaluation_valid: false`, und der Skill-Score misst weiterhin die Konstantentabelle (A-01).
**Das ist der beabsichtigte Zustand:** Phase I macht die Unwissenheit sichtbar, Phase II und
AP-30 beseitigen sie. Wer nach Phase I bessere Zahlen erwartet hat, hat den Zweck missverstanden —
mehrere Kennzahlen sind jetzt *schlechter* oder *undefiniert*, weil sie vorher unbegründet gut aussahen.

### Zwei bewusste Nicht-Änderungen

1. **V-3 nicht mit Fixtures geschlossen.** Die 8 Kontrollen brauchen Replay-Inputs, damit die
   Fehlalarmrate einen Nenner bekommt. Synthetische Inputs hätten eine Rate erzeugt, die genauso
   wenig über das Modell aussagt wie die heutige strukturelle Null — nur schwerer als Artefakt
   erkennbar, weil sie plausibel aussieht. Stattdessen: Zustand explizit markiert
   (`evaluation_valid: false`) und die Anforderung an **AP-30.4** gehängt, das reale Bundles
   ohnehin zieht.
2. **`alarm_minimum_status` bei S1 belassen.** Der `governance_record` empfiehlt S2, und das ist
   fachlich gut begründet (ein mildes S1 auf einer Kontrolle ist kein voller Fehlalarm). Aber die
   Umstellung **senkt die eigene Fehlalarmrate**. Eine solche Änderung unmittelbar nach dem Bau der
   Messmechanik ohne Owner-Freigabe zu setzen, wäre genau das Muster, das dieses Audit rügt.
   Owner-Entscheid ausstehend; der Mechanismus ist gebaut und getestet, nur der Wert ist konservativ.

### Nächster wissenschaftlicher Hebel

Unverändert **Phase II (V-8..V-11)**, getragen von AP-13/26/30: SPC-konforme Anomalie
(Baseline ohne Prüfpunkt, Stichproben-σ, ≥20 Punkte), EWMA/CUSUM gegen schleichende Eskalation,
Persistenz/Hysterese, und die Trennung von Datenlage und Bedrohungslage (S0/S6-Problem, A-03/A-05).
Erst danach lohnt Phase III (UCDP konsumieren, Normalisierung, INFORM-Aggregation).
