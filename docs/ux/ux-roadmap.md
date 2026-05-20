# SIASA UX-Roadmap

## Analyse der aktuellen generatorbasierten GUI

### Ist-Zustand (Stand: 2026-05-20)

**Generator:** `src/siasa/gui/local_app.py` (2.436 Zeilen, reines Python, f-Strings)

**Generierte Seiten (13 gesamt):**

| Seite | Datei | Reife (UX) |
|---|---|---|
| World Overview / Anomaly Map | `index.html` | 🟡 Funktional, visuell schwach |
| Country Profile | `countries/{ID}.html` | 🟡 Funktional, informationsreich aber unstrukturiert |
| Domain Detail | `domains/{ID}-{Domain}.html` | 🟡 Funktional, tabellarisch |
| Source / Coverage | `coverage.html` | 🟡 Funktional, SVG-Charts vorhanden |
| Reports / Exports | `reports.html` | 🟢 Einfach, funktioniert gut |
| System Status / Runs | `runs.html` | 🟡 Funktional |
| Yearly Trends | `trends.html` | 🟡 SVG-Charts, JS-Filter vorhanden |
| Current Events | `events.html` | 🟡 JS-Filter vorhanden |
| Cross-Country Comparison | `comparison.html` | 🟡 Tabelle, JS-Filter |
| Validation / Backtest | `validation.html` | 🔴 Daten vorhanden, visuell sehr roh |
| Traceability / Lineage | `traceability.html` | 🔴 Tabellen-basiert, keine visuelle Hierarchie |
| Analyst Annotations | `annotations.html` | 🟡 localStorage-CRUD vorhanden, aber unpoliert |
| Demo / Release Readiness | `readiness.html` | 🟡 Funktional |

**Kritische UX-Schwäche heute:**
- **Helles Design** (weißer Hintergrund, schwarzer Text) — kein Dark Dashboard
- **Keine Design-Systematik** — CSS-Regeln verstreut, inkonsistente Abstände
- **Inline-Style-Fragmente** — Farben direkt in f-Strings, kein CSS-Klassen-System
- **Keine visuelle Hierarchie** zwischen Panels, Abschnitten, KPIs
- **Navigation funktional aber ungestylt**
- Trotzdem: Semantik, Funktionalität und Datenfluss sind korrekt implementiert

**Was bereits stark ist:**
- Inline-SVG-Charts (Liniendiagramme, Meter, World-Map-Visualisierung) — bauen darauf auf
- Vanilla-JS-Filterlogik — gut strukturiert, behalten
- Semantische Statusfarben (`_status_color()`, `_band_color()`) — Logik stimmt, Farben anpassen
- `html.escape()` konsequent eingesetzt — beibehalten
- Self-contained (keine externen Assets) — beibehalten

---

## UX-Iterationsplan

### Iteration 1 — Dark Dashboard Foundation `[AKTUELL]`

**Ziel:** Globales Dark-Dashboard-Styling durch Modernisierung der `_page()` CSS-Funktion.  
Keine strukturellen HTML-Änderungen — nur CSS und Typografie.

**Scope:**
- `_page()` CSS-Block vollständig ersetzen durch Dark-Dashboard-System (siehe `design-system.md`)
- Navigation: dunkel, sticky, strukturiert
- Body: dunkler Hintergrund, helle Schrift
- Tabellen: Dark-Styling (Header, Zeilen, Hover)
- `<pre>`/`<code>`: technische Code-Darstellung
- Statusfarben in `_status_color()` und `_band_color()` auf neue Palette anpassen
- Badge-Komponente (`.uncertainty-badge`) modernisieren

**Risiken:**
- Test-Assertions auf CSS-Klassen oder Farbwerte könnten brechen → prüfen und anpassen
- Kontrastverhältnisse müssen für alle Statusfarben WCAG AA (4.5:1) erfüllen

**Erwartetes Ergebnis:** Alle 13 Seiten sehen einheitlich dunkel und professionell aus — ohne HTML-Struktur-Änderung.

---

### Iteration 2 — Panel- und Layout-System

**Ziel:** Konsistente Panel-/Card-Struktur einführen. Alle Abschnitte in `_page()` und Render-Funktionen nutzen das Panel-System.

**Scope:**
- `.panel` / `.panel-header` CSS-Klassen einführen
- Section-Wrapper in relevanten Render-Funktionen (`_render_index`, `_render_country`, etc.)
- KPI-Card-Komponente für Kennzahlen-Blöcke
- Navigation: aktiver Link hervorheben

**Risiken:**
- HTML-Struktur-Änderungen können mehr Tests brechen als Iteration 1
- Readmodel-gebundene Inhalte nicht strukturell verändern

---

### Iteration 3 — KPI-Header und Status-Zones

**Ziel:** Jede Seite erhält eine strukturierte Header-Zone mit KPIs, Status-Badges und Meta-Informationen.

**Scope:**
- `index.html`: KPI-Leiste (Länderanzahl, kritische Anomalien, Coverage-Rate)
- `countries/{ID}.html`: Country-KPI-Block (Gesamtstatus, Domains, letzte Aktualisierung)
- `runs.html`: System-Status-Header
- `readiness.html`: Readiness-Score-KPIs

**Risiken:**
- KPI-Inhalte aus Readmodels müssen korrekt extrahiert werden — Contract-Risiko niedrig (read-only)

---

### Iteration 4 — Tabellen- und Listen-Modernisierung

**Ziel:** Alle Tabellen erhalten einheitliches Dark-Styling, Hover-States, kompakte Typografie.  
Event-Listen werden als strukturierte Items gerendert.

**Scope:**
- Tabellen-CSS komplett systematisieren
- Event-Listen auf `events.html` und `index.html` als Panel-Items
- Annotation-Workflow (`annotations.html`) visuell aufwerten

**Risiken:**
- Event-Listen haben JS-Filter — CSS-Änderungen dürfen JS-Selektoren nicht brechen

---

### Iteration 5 — Chart- und SVG-Systematisierung

**Ziel:** Alle SVG-Charts nutzen das Farb- und Stilsystem aus dem Design System.

**Scope:**
- `_render_line_chart()`: dunklere Hintergründe, neue Linienfarben, Grid-Linien
- `_render_metric_meter()`: Farbgebung nach Band-System
- `_render_world_map_visualization()`: Marker-Styling konsistenter

**Risiken:**
- SVG ist inline und hardcoded — Änderungen müssen in Python-Strings erfolgen
- Kein externe Rendering-Library einführen

---

### Iteration 6 — Validation / Traceability / Coverage Uplift

**Ziel:** Die daten-intensiven analytischen Seiten bekommen bessere visuelle Struktur.

**Scope:**
- `validation.html`: Pass/Fail-Badge-System, Score-KPI
- `traceability.html`: Cluster-Karten statt flache Tabelle, faltbare Sektionen
- `coverage.html`: Trust-Visualisierung verbessern

**Risiken:**
- Diese Seiten sind besonders nah an Readmodel-Verträgen — keine Datenstruktur ändern

---

### Iteration 7 — Accessibility und Responsive-Grundlage

**Ziel:** Mindest-Accessibility und mobile Nutzbarkeit sicherstellen.

**Scope:**
- `aria-label` auf interaktive Elemente
- Tabellen horizontal scrollbar auf kleinen Viewports
- Kontrastverhältnisse WCAG AA prüfen und korrigieren
- `focus`-States für Tastaturnavigation

**Risiken:** Gering — reine CSS- und HTML-Attribute-Ergänzungen

---

### Spätere Iterationen (Post-MVP)

- **Rolle-basiertes UI-Verhalten** (strukturelle Hooks vorhanden, GUI-Verhalten noch schwach)
- **Source Lineage / Epidemiology Visualisierung** (aktuell nur Traceability-Tabelle)
- **Erweiterte Annotation-Features** (persistente Speicherung statt localStorage)
- **Interaktive Karten-Overlay** (World Map mit echten Geo-Koordinaten)
- **Export / Print-Styles**

---

## Aktueller Status-Überblick

| Iteration | Status | Priorität |
|---|---|---|
| 1 — Dark Dashboard Foundation | 🔵 Bereit | Hoch |
| 2 — Panel- und Layout-System | ⚪ Geplant | Hoch |
| 3 — KPI-Header und Status-Zones | ⚪ Geplant | Mittel |
| 4 — Tabellen- und Listen-Modernisierung | ⚪ Geplant | Mittel |
| 5 — Chart- und SVG-Systematisierung | ⚪ Geplant | Mittel |
| 6 — Validation / Traceability / Coverage Uplift | ⚪ Geplant | Niedrig |
| 7 — Accessibility und Responsive-Grundlage | ⚪ Geplant | Niedrig |

---

*Erstellt: 2026-05-20 | Version: 1.0.0*
