# Wissenschaftliche Initialbestimmung der SIASA-Schwellen & -Gewichte (AP-24-Input)

Stand: 2026-06-26 · Quelle: Deep-Research-Lauf (`wf_281f2c2e-410`) — 6 Such-Winkel, 29 Quellen,
126 Claims → 25 verifiziert → 17 bestätigt, 8 verworfen. **Hinweis:** Die automatische Synthese-/
Verifikationsstufe brach am Session-/Rate-Limit ab; dieser Bericht ist aus den verifizierten Claims +
den gefetchten Primärquellen + etabliertem Standardwissen synthetisiert.

> **Konfidenz-Marker:** **✓✓** = in diesem Lauf quellenbelegt (3-0 adversarial bestätigt) ·
> **✓** = Primärquelle gefetcht, Einzel-Claim nicht re-verifiziert (Limit) ·
> **○** = etablierte Konvention/Standardwissen (in diesem Lauf nicht einzeln belegt).

Bezug: Befund **F11** / Arbeitspaket **AP-24 (Schwellen-Governance, „Magic Numbers")**. Begleitartefakte:
governte Config `vmodel/project/scoring_thresholds.yaml`, Sensitivitäts-Werkzeug `scripts/threshold_sensitivity.py`.

---

## Executive Summary

Die wichtigste belegte Erkenntnis ist **methodologisch, nicht numerisch**: Die maßgebliche Literatur
(OECD/JRC-Handbook, INFORM) sagt ausdrücklich, dass **Gewichte und Schwellen fundamental Werturteile sind —
keine rein empirisch ableitbaren Konstanten** (✓✓). Die hartcodierten Werte sind also nicht per se falsch,
sondern *unbegründet*. „Wissenschaftlich sinnvoll initial bestimmen" heißt:
1. Defaults aus **Konvention** (SPC-σ-Vielfache, 90/95 %-CIs) oder aus **publizierten Analog-Systemen**
   (INFORM, ViEWS, GUM) übernehmen;
2. jede Wahl **dokumentiert begründen** (Owner-Hoheit, aber nachvollziehbar);
3. gegen die **Korrelationsstruktur der Daten validieren** (INFORM verlangt genau das ✓✓);
4. sobald Ground-Truth da ist, **kalibrieren**;
5. per **Sensitivitätsanalyse** zeigen, welche Parameter überhaupt zählen — ein INFORM-Severity-Re-Audit fand,
   dass **nur 11 von 35 Indikatoren** echte Information tragen (✓✓).

---

## Übergreifende Methodik (am stärksten belegt)

| Prinzip | Beleg |
|---|---|
| Gewichte/Schwellen = **Werturteile**, legitime Owner-Hoheit (deckt sich mit `AGENTS.md`) | OECD/JRC-Handbook ✓✓ |
| Jede Wahl (Normalisierung, Gewichtung, Schwelle, Aggregation) braucht **data-driven Begründung**; Nominalgewichte gegen Pearson-r²/PCA-Struktur prüfen | INFORM Severity / JRC-Audit ✓✓ |
| Bei knapper Ground-Truth: **fixe/Experten-gesetzte Grenzen** statt Daten-Extrema (stabil, outlier-robust) | INFORM min-max-Normalisierung ✓✓ |
| **Equal weighting** = häufigster Default, aber verschleiert ggf. fehlende statist. Basis + **Double-Counting** bei kollinearen Größen | OECD/JRC ✓✓ |
| **Robustheit = kombinierte Unsicherheits- + Sensitivitätsanalyse** über alle subjektiven Wahlen | OECD/JRC ✓✓ |
| Parameter NICHT als „zweitrangig" annehmen — die Behauptung „INFORM robust gegen Aggregations-/Gewichtungswahl" wurde **verworfen (1-2)**; das Gegenteil (24/35 Indikatoren redundant) zeigt: Wahlen zählen → **testen statt annehmen** | verworfen + ✓✓ |
| Pipeline: Konvention/Analog → Experten-Elicitation (SHELF/Cooke) → Kalibrierung gegen kuratierte Events → Sensitivitäts-Pruning | Standard ○ / SHELF ✓ |

---

## Karte pro Parameter-Familie

### 1 · Anomalie→D-Status-Schwellen
Aktuell: D1 `<0.2`, D2 `<0.5`, D3 `<1.0`, D4 `≥1.0`; `ANOMALY_UPPER_BOUND=1.5`; `_MIN_SERIES_POINTS=4`;
Roll-Fenster 7/30 d; Baselines 30/90/365 d.
- **Methode:** SPC-Kontrollgrenzen in σ-Vielfachen; Konvention **±2σ = Warnung, ±3σ = Aktion/„out of control"**
  (Shewhart, Western-Electric-Rules) ○.
- **Empfehlung (Initial-Default):** Cutpoints an σ binden statt frei wählen — D1 `<1σ` · D2 `1–2σ` ·
  D3 `2–3σ` · D4 `≥3σ`, also **~1.0 / 2.0 / 3.0** und Bound **~3.0–3.5** statt 0.2/0.5/1.0/1.5. Die aktuellen
  Werte liegen **weit unter** der SPC-Konvention (z=1.0 → D4 „kritisch", obwohl 1σ nur ~16 %-Tail ist) →
  systematisches **Over-Flagging**. `_MIN_SERIES_POINTS=4` ist für eine vertrauenswürdige σ-Schätzung **zu wenig**
  (SPC: ~20–25 Subgruppen; klein-Stichprobe → t-/c4-Bias-Korrektur). Fenster 7/30 + Baselines 30/90/365 sind als
  Mehr-Skalen-Ansatz vertretbar.
- **Referenz:** NIST/Shewhart SPC, Western-Electric-Rules, EWMA/CUSUM (✓). ⚠️ Die Run-Claim, die 3σ explizit der
  SIASA-D4-Schwelle zuordnete, wurde **verworfen (0-3)** — vermutlich wegen der editorialen Zuordnung; die
  2σ/3σ-Konvention selbst ist Standard.

### 2 · Multi-Domain-Aggregation S0–S6 *(am stärksten belegt)*
Aktuell: Zähl-Regeln über D2/D3/D4-Domain-Anzahl.
- **Methode:** Composite-Indicator-Aggregation; Kernentscheidung = **Kompensierbarkeit** (darf ein Defizit in
  einer Domäne durch Überschuss in anderer ausgeglichen werden?) ✓✓. Die Zähl-Regel ist faktisch
  **nicht-kompensatorisch** — genau dafür nutzt INFORM den **geometrischen Mittelwert**
  (Risk = HE^⅓·V^⅓·LCC^⅓, =0 wenn eine Dimension 0) ✓✓. Deckt sich mit `AGENTS.md`-Regel 9 (kein naiv-additives Fusion).
- **Empfehlung:** Zähl-Regel als nicht-kompensatorische Wahl **vertretbar** — aber dokumentieren + per
  Korrelation/PCA validieren ✓✓. Prinzipientreuer: **geometrisches Mittel** der Domänen-Severities, dann
  **continuous→S0–S6 via fixe ROUNDUP-Cutpoints** (INFORM-Severity-Präzedenz: 0–5 → 5 Stufen ✓✓). Equal
  domain-weights als Default, gegen die Struktur geprüft.
- **Referenz:** INFORM Risk + INFORM Severity + OECD/JRC ✓✓ — die genutzte HDX-INFORM-Quelle ist das *direkte* Analog.

### 3 · Daten-Suffizienz
Aktuell: Coverage `≥0.6`, Freshness `≤168h` (Domain C `336h`), `≥2` Features/Domain.
- **Methode:** Datenqualitäts-Dimensionen (Vollständigkeit, Timeliness) — operative Policy-Schwellen,
  Owner-Hoheit ○.
- **Empfehlung:** als governte Config halten (teils schon in `freshness_config.yaml`); per operativer Refresh-
  Kadenz begründen; **min-Features an die σ-Schätzung koppeln** (konsistent mit Familie 1). INFORM nutzt selbst
  Experten-gesetzte Bounds bei dünner Datenlage ✓✓.
- **Referenz:** Datenqualitäts-Standards (DAMA/ISO-8000-Stil) ○; INFORM-Coverage-Handling ✓✓.

### 4 · Bayes-Status (probabilistisch)
Aktuell: Zentren D0=0.0/D1=0.1/D2=0.35/D3=0.65/D4=1.0; σ=0.2; 80 %-CI.
- **Methode:** Experten-Prior-Elicitation (**SHELF**, **Cooke's Classical Method**) ✓; oder aus der
  Anomalie-Score-Verteilung je Status kalibrieren.
- **Empfehlung:** Zentren **konsistent mit den D-Cutpoints** (Familie 1) als Bereichs-Mittelpunkte setzen;
  σ=0.2 bei ~0.25-Abständen → **starke Überlappung** (Unter-Diskriminierung) → elicitieren/kalibrieren.
- **Referenz:** SHELF / Cooke / O'Hagan „Uncertain Judgements" (2006); Gosling (2018) SHELF ✓.

### 5 · Cross-Domain-Fusion
Aktuell: Reliabilität 1.0/0.6/0.2; Kontradiktion bei Status-Gap `≥2`; Confidence `max(0.3, 1−0.15·gap)`.
- **Methode:** Evidenz-Reliabilitäts-Gewichtung & Discounting; **Dempster-Shafer**; **NATO-Admiralty-
  Reliabilitätsskala** (A–F / 1–6) ○.
- **Empfehlung:** die 6-stufige NATO-Reliabilitäts-Credibility-Skala gibt ein **prinzipielles diskretes Mapping** —
  Suffizienz-Tiers darauf abbilden; Gewichte bleiben Werturteile (Owner) aber begründet; Dempster-Shafer liefert
  einen formalen Konflikt-Massen-Rahmen für die Kontradiktions-Logik.
- **Referenz:** NATO AJP-2.1 Reliability/Credibility-Skala ○; Dempster-Shafer-Evidenztheorie.

### 6 · Unsicherheits-Propagation
Aktuell: 90 %-CI z=1.645; Stufen-Rauschen 10 % (Extraktion) / 15 % (Scoring) / 5 % (Fusion), in Quadratur.
- **Methode:** **GUM (JCGM 100)** — unabhängige Unsicherheiten **in Quadratur (RSS)** kombinieren; die Quadratur
  ist GUM-korrekt ○.
- **Empfehlung:** z=1.645 (90 %) korrekt; ggf. **95 % (z=1.96)** für Headline-Intervalle (Konvention). Die
  10/15/5 % sind **Type-B-Schätzungen** (Experten-Annahme) → als solche dokumentieren, später durch Type-A
  (datenbasiert) ersetzen.
- **Referenz:** GUM JCGM 100, Type-A/Type-B-Unsicherheitsbudget ○.

### 7 · Skill-/Validierungs-Metriken
Aktuell: Skill = 0.6·Detektion + 0.4·Domain-Match; Replay-Evidenz 0.4/0.3/0.2/0.1; Tiers 0.95/0.75/0.5;
Regression 10 %-Drop, warn>10 %/fail>30 %.
- **Methode:** **Forecast-Verification-Wissenschaft.** Die *geplanten* AP-28-Metriken (Brier, Fehlalarmrate/FAR,
  POD, No-Skill-Baseline, Vorlaufzeit, ROC/AUC) sind **exakt die etablierten** — „Skill" ist per Definition
  **relativ zu einer Referenz** (Brier Skill Score vs. Klimatologie; Heidke/Peirce) ○.
- **Empfehlung:** die ad-hoc-Komposit-Gewichte 0.6/0.4 **ersetzen durch separat berichtete Standardmetriken**
  (Brier, BSS vs. „immer-S3"-Baseline, POD, FAR, AUC, Lead-Time) statt eines Misch-Scores — so machen es
  ViEWS/WMO. Regressions-Schwellen an das **Konfidenzintervall des Skill-Scores koppeln** (Abfall im Rauschen ≠
  echte Regression).
- **Referenz:** WMO/CAWCR-Forecast-Verification; ViEWS (Violence Early-Warning System), ICEWS, GDELT-Forecasting ✓.

### 8 · Info-Epidemiologie
Aktuell: Amplifikation bei Wert `>1.5×` der Erstbeobachtung.
- **Methode:** Diffusions-/Epidemie-Modelle (**R₀**, Verdopplungszeit) ○.
- **Empfehlung:** das fixe 1.5×-Verhältnis durch ein **Wachstumsraten-/R₀-Kriterium** ersetzen
  (Exponential-Wachstums-Detektion bzw. k·σ über der Diffusions-Baseline) — konsistent mit dem z-Score-Ansatz
  aus Familie 1.
- **Referenz:** R₀/Epidemie-Schwelle, Informations-Diffusionsmodelle ✓.

---

## Verifizierte Kern-Quellen

| Quelle | Belegt |
|---|---|
| OECD/JRC *Handbook on Constructing Composite Indicators* (2008) | Gewichte = Werturteile; equal-weight-Caveat; linear-vs-geometrisch; Sensitivitätsanalyse ✓✓ |
| INFORM Risk Methodology (JRC, DRMKC) | hierarchische Aggregation, geometrisches Mittel, equal weights, Experten-Bounds ✓✓ |
| INFORM Severity Methodology (JRC, 2020) | hybride Aggregation (70/30, 33/66), continuous→ordinal ROUNDUP, data-driven-Begründungspflicht ✓✓ |
| JRC Statistical Audit / Faktor-Re-Analyse (PMC9887746) | PCA-Strukturvalidierung; **nur 11/35 Indikatoren informativ** ✓✓ |
| NIST SPC-Handbook, Western-Electric-Rules, EWMA/CUSUM | SPC-Kontrollgrenzen (gefetcht) ✓ |
| GUM (JCGM 100), NATO AJP-2.1 | Unsicherheitsbudget / Reliabilitätsskala (gefetcht) ✓ |
| CAWCR Forecast Verification; ViEWS-Papers (J. Peace Research) | Skill-/Verification-Metriken (gefetcht) ✓ |
| SHELF reading-list (O'Hagan 2006, Gosling 2018), Cooke Classical Method | Experten-Elicitation (gefetcht) ✓ |
| R₀-Notes (Berkeley), Informations-Diffusion (Nature) | Amplifikations-/Epidemie-Schwellen (gefetcht) ✓ |

## Ehrliche Einordnung des Recherche-Stands
**Familie 2 + die übergreifende Methodik** sind quellenstark belegt (INFORM/OECD-JRC, 3-0). Die Quellen für
**Familien 1, 4, 5, 6, 7, 8** wurden gefetcht (als Primärquellen gelistet), ihre Einzel-Claims aber wegen des
Rate-Limits **nicht mehr 3-0-verifiziert** — die dortigen Empfehlungen stützen sich auf diese Quellen +
etablierte Konvention, nicht auf frische adversariale Verifikation. Eine erneute, gezielte Verifikation der
offenen Familien ist möglich (nach Limit-Reset).

## Operationalisierung
- **Governte Single-Source-of-Truth:** `vmodel/project/scoring_thresholds.yaml` — jede Schwelle mit `current`,
  `recommended_initial`, `rationale`, `reference`, `governance: owner_authority` und `wired_to_config`-Flag.
- **Live verdrahtet (AP-24-Slice):** Anomalie-Bound/-Mindestpunkte (`scoring/anomaly.py`) und D-Status-Cutpoints
  (`scoring/domain_status.py`) lesen ihre Werte aus der Config (behavior-preserving, Fallback = aktuelle Werte).
- **Sensitivitätsanalyse:** `scripts/threshold_sensitivity.py` perturbiert jede governte Schwelle und misst den
  Einfluss auf die Status-/Skill-Ergebnisse über die Referenzfälle (operationalisiert die OECD/JRC-Empfehlung,
  „welche Parameter zählen wirklich").
