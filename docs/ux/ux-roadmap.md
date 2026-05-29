# SIASA UX-Roadmap

## Analyse der aktuellen generatorbasierten GUI

### Ist-Zustand (Stand: 2026-05-29)

**Generator:** `src/siasa/gui/local_app.py` (~4.500 Zeilen, reines Python, f-Strings)

**Generierte Seiten (13 gesamt):**

| Seite | Datei | Reife (UX) |
|---|---|---|
| World Overview / Anomaly Map | `index.html` | 🟢 Interaktive SVG-Karte, Natural Earth 110m, 29 Länder |
| Country Profile | `countries/{ID}.html` | 🟢 Dark panels, KPI-Header, strukturiert |
| Domain Detail | `domains/{ID}-{Domain}.html` | 🟢 Charts, Panel-Struktur |
| Source / Coverage | `coverage.html` | 🟢 Trust-Visualisierung, table-wrap, responsive |
| Reports / Exports | `reports.html` | 🟢 Kategorisiert, Download-Buttons, Suchfilter |
| System Status / Runs | `runs.html` | 🟢 KPI-Header, Panel-Struktur |
| Yearly Trends | `trends.html` | 🟢 SVG-Charts mit Y-Achse, Area-Fill, Grid |
| Current Events | `events.html` | 🟢 KPI-Header, Smart-Filter-Counter, Panel-Items |
| Cross-Country Comparison | `comparison.html` | 🟢 Tabelle, JS-Filter |
| Validation / Backtest | `validation.html` | 🟢 KPI-Grid, Verdict-Bars, Replay Attention Layer |
| Traceability / Lineage | `traceability.html` | 🟢 Collapsible-Sektionen, Cluster-Karten |
| Analyst Annotations | `annotations.html` | 🟢 localStorage Create/Edit/Delete-Modal |
| Demo / Release Readiness | `readiness.html` | 🟢 Dual-KPI, Failure-Drill, Operator-Digest |

**Was bereits stark ist:**
- Vollständiges Dark-Dashboard-Design (AEGIS Tactical Design System)
- Interaktive SVG-Weltkarte (Natural Earth 110m GeoJSON, 177 Länder-Outline)
- 29 Länder in sample_artifacts (alle P1/P2/P3 MVP-Länder)
- Inline-SVG-Charts mit Y-Achse, Grid, Area-Fill, responsiv
- Vanilla-JS-Filterlogik, Accessibility (focus-visible, aria-label, skip-nav)
- Responsive CSS (900px / 600px Breakpoints)
- Role-based UI (viewer / analyst / admin über `--ui-role`)
- Self-contained (keine externen Assets)

---

## UX-Iterationsplan

### ✅ Iteration 1 — Dark Dashboard Foundation `[ABGESCHLOSSEN]`
**Commit:** `d4bc589`  
Globales Dark-Dashboard-Styling in `_page()` — Navy-Black Theme, neue Statusfarbenpalette.

---

### ✅ Iteration 2 — AEGIS Tactical Design System `[ABGESCHLOSSEN]`
**Commit:** `746ec25`  
Vollständiges AEGIS-Designsystem: Space Grotesk / IBM Plex Mono, Panel-System, KPI-Cards, Badge-Komponenten.

---

### ✅ Iterationen 3–9 — Strukturelle GUI-Uplifts `[ABGESCHLOSSEN]`
**Commit:** `650a581`  
Panel-/Layout-System, KPI-Header-Zones, Tabellen-Modernisierung, Chart-Systematisierung, alle Seiten strukturell aufgewertet.

---

### ✅ Events-Seite — KPI + Panel `[ABGESCHLOSSEN]`
**Commit:** `5a70ac9`  
Events-Seite mit KPI-Header, Panel-Struktur, Smart-Filter-Counter.

---

### ✅ Chart & Meter Uplift `[ABGESCHLOSSEN]`
**Commit:** `7530c86`  
Y-Achse, Grid-Linien, Area-Fill, responsive SVG-Charts, neues Meter-Layout.

---

### ✅ World Map — Interaktive SVG `[ABGESCHLOSSEN]`
**Commit:** `efcd914` → `f2caac9`  
Interaktive SVG-Weltkarte, dann Natural Earth 110m GeoJSON (177 Länderkonturen, 29 MVP-Länder farbkodiert nach Status).

---

### ✅ Iteration 6 — Validation & Traceability UX Uplift `[ABGESCHLOSSEN]`
**Commit:** `6d27681`  
Validation-Seite: KPI-Grid, Active Case Panel, Domain-Signal-Panel, Curated Library, Replay Attention Watchlist. Traceability: Cluster-Karten, collapsible Sektionen.

---

### ✅ Iteration 7 — Accessibility & Responsive `[ABGESCHLOSSEN]`
**Commit:** `ab520fc`  
- `*:focus-visible` Outline-System (WCAG-konform, blau `#388bfd`)
- Skip-Nav-Link (`#main-content`)
- `<nav aria-label='Main navigation'>`, `<main id='main-content'>`
- `scope='col'` auf alle `<th>` Tabellenköpfe
- `.table-wrap` — horizontaler Scroll auf kleinen Viewports
- Media Queries: 900px (2-Spalten-KPI) und 600px (1-Spalte, kompakte Nav)

---

### ✅ Reports/Exports UX `[ABGESCHLOSSEN]`
**Commit:** `ab520fc`  
- `.btn-download` Styling für alle Download-Links
- Berichte nach Kategorie gruppiert (`<details>`/`<summary>`)
- Suchfilter auf Reports-Seite
- Dateigröße im Download-Link (falls `size_bytes` vorhanden)

---

### ✅ Annotation Create/Edit/Delete `[ABGESCHLOSSEN]`
**Commit:** `ab520fc`  
- Modal-Dialog mit Formular (Country, Domain, Run-ID, Note, Author)
- Create / Edit / Delete via localStorage
- Dynamisches Re-Render der Annotation-Liste
- Backdrop-Click zum Schließen

---

### ✅ Länder-Coverage — Alle 29 MVP-Länder `[ABGESCHLOSSEN]`
**Commit:** `ab520fc`  
- `sample_artifacts/readmodels/country_profiles/`: 30 JSON-Profile
- `sample_artifacts/readmodels/domain_details/`: Alle aktiven Domänen pro Land
- `world_map.json`: Alle 29 Länder mit realistischen S0–S4-Statuswerten
- Export-Dateien für alle neuen Länder

---

## Aktueller Status-Überblick

| Iteration | Status | Priorität |
|---|---|---|
| 1 — Dark Dashboard Foundation | ✅ Abgeschlossen | — |
| 2 — AEGIS Tactical Design System | ✅ Abgeschlossen | — |
| 3–9 — Strukturelle GUI-Uplifts | ✅ Abgeschlossen | — |
| Events / Chart / World Map | ✅ Abgeschlossen | — |
| 6 — Validation & Traceability UX | ✅ Abgeschlossen | — |
| 7 — Accessibility & Responsive | ✅ Abgeschlossen | — |
| Reports/Exports UX | ✅ Abgeschlossen | — |
| Annotations Create/Edit | ✅ Abgeschlossen | — |
| Länder-Coverage (29 Länder) | ✅ Abgeschlossen | — |

---

## Offene Post-MVP Iterationen

| Feature | Priorität | Beschreibung |
|---|---|---|
| Erweiterte Annotation-Persistenz | Mittel | Persistente Speicherung statt localStorage (Server-side) |
| Source Lineage Graph-Visualisierung | Mittel | Epidemiology-Graph statt Tabelle (aktuell nur Traceability-Tabelle) |
| Interaktive Karten-Overlay | Niedrig | World Map mit Geo-Koordinaten-Pins und Drill-Down-Zoom |
| Export / Print-Styles | Niedrig | CSS `@media print` für Reports-Seite |
| Server-seitige Rollen-/Permissions-Governance | Post-MVP | Identity/Permission-Layer für Produktivbetrieb |
| WCAG AA Kontrast-Vollaudit | Niedrig | Systematische Überprüfung aller Statusfarben S0–S6 |

---

*Erstellt: 2026-05-20 | Letzte Aktualisierung: 2026-05-29 | Version: 2.0.0*
