# SIASA Design System

## Design-Ziel

SIASA ist ein analytisches Monitoring-/Assessment-System. Die GUI soll wie ein professionelles Operations-/Intelligence-Dashboard wirken:
**modern, technisch, ruhig, informationsreich, analytisch belastbar**.

Es ist **kein** Marketing-Frontend, kein Consumer-Produkt, keine gamifizierte App.

---

## Farbkonzept

### Hintergrund-Hierarchie

| Ebene | Verwendung | Aktuell | Ziel |
|---|---|---|---|
| `bg-base` | Body-Hintergrund | `#1a1a1a` (implizit) | `#0f1117` sehr dunkles Navy-Schwarz |
| `bg-surface` | Cards / Panels | `#fff` (hell!) | `#161b22` dunkle Fläche |
| `bg-raised` | Nested panels, Tabellen-Header | — | `#1c2333` leicht erhoben |
| `bg-overlay` | Hover-States, aktive Navigation | — | `#21262d` |

**Problem heute:** Das aktuelle Design ist helles, minimales HTML mit weißem Hintergrund — kein Dark Dashboard.

### Statusfarben (semantisch — nicht ändern!)

Diese Farben sind an Readmodel-Statuswerte gebunden und dürfen nicht willkürlich umdefiniert werden:

| Status | Bedeutung | Aktuelle Implementierung | Ziel-Farbe |
|---|---|---|---|
| S0 | Unknown/No data | `color: #999` | `#6e7681` |
| S1 | Data present, unvalidated | `color: #aaa` | `#8b949e` |
| S2 | Low confidence | `color: orange` | `#d29922` amber |
| S3 | Moderate | `color: goldenrod` | `#e3b341` gold |
| S4 | Meaningful signal | `color: #3399ff` | `#388bfd` blue |
| S5 | Strong signal | `color: #cc44ff` | `#bc8cff` violet |
| S6 | Confirmed / Critical | `color: red` | `#f85149` red |

**S0–S2:** neutral/grey → amber (datenschwach, unsicher)
**S3:** Warnstufe → gold
**S4–S5:** bedeutsame Signale → blau / violett
**S6:** kritisch → rot

### Band-Farben (Coverage / Confidence / Freshness)

| Band | Bedeutung | Ziel-Farbe |
|---|---|---|
| `high` | Gut abgedeckt, frisch | `#3fb950` grün |
| `medium` | Teilweise | `#d29922` amber |
| `low` | Schwach, veraltet | `#f85149` rot |
| `none` / `unknown` | Keine Daten | `#6e7681` grau |

### Akzentfarben (UI-Struktur)

| Zweck | Farbe |
|---|---|
| Primäre Aktion / Fokus | `#388bfd` blau |
| Navigation aktiv | `#58a6ff` hellblau |
| Border / Divider | `#30363d` |
| Text primär | `#e6edf3` |
| Text sekundär | `#8b949e` |
| Text disabled | `#484f58` |

---

## Typografie

**Philosophie:** Modern, technisch, sehr gut lesbar. Kein dekoratives Serif.

| Element | Schrift | Größe | Gewicht | Farbe |
|---|---|---|---|---|
| Body | system-ui, -apple-system, "Segoe UI", sans-serif | 14px | 400 | `#e6edf3` |
| H1 (Page Title) | — | 1.4rem | 600 | `#e6edf3` |
| H2 (Section) | — | 1.1rem | 600 | `#c9d1d9` |
| H3 (Panel) | — | 0.95rem | 600 | `#8b949e` uppercase |
| KPI Value | — | 1.6–2rem | 700 | semantische Farbe |
| KPI Label | — | 0.75rem | 400 | `#8b949e` uppercase |
| Table Body | Monospace für Codes, IDs | 13px | 400 | `#e6edf3` |
| Code / Pre | "Cascadia Code", "Fira Code", monospace | 12px | 400 | `#79c0ff` |
| Badge / Tag | — | 11px | 500 | je nach Semantik |
| Nav | — | 13px | 500 | `#8b949e` |

---

## Spacing-System

Einheitliches 4px-Raster:

| Token | Wert | Verwendung |
|---|---|---|
| `xs` | 4px | Intra-Komponenten-Abstände |
| `sm` | 8px | Badge-Padding, kompakte Items |
| `md` | 16px | Standard Card-Padding |
| `lg` | 24px | Section-Abstände |
| `xl` | 32px | Page-Level-Trennung |

---

## Layout-Regeln

### Seiten-Grundstruktur

```
┌─────────────────────────────────────────────────────┐
│  NAV BAR  (sticky, dark, system status, nav links)  │
├───────────┬─────────────────────────────────────────┤
│  SIDEBAR  │  MAIN CONTENT AREA                      │
│  (opt.)   │  ┌──────────────────────────────────┐   │
│           │  │  PAGE HEADER (title, KPIs, meta) │   │
│           │  ├──────────────────────────────────┤   │
│           │  │  FILTER / CONTROL BAR            │   │
│           │  ├──────────────────────────────────┤   │
│           │  │  PRIMARY CONTENT                 │   │
│           │  │  (table / chart / panel grid)    │   │
│           │  └──────────────────────────────────┘   │
└───────────┴─────────────────────────────────────────┘
```

- **Primär desktop-orientiert** (min 1280px nutzbar, optimiert für 1440px+)
- Max-width: `1600px`, zentriert
- Navigation: sticky top, `48px` Höhe
- Content-Padding: `24px` horizontal

### Grid-Prinzipien

- KPI-Cards: 3–5 pro Zeile, `repeat(auto-fit, minmax(180px, 1fr))`
- Panel-Grid: max 2–3 Spalten, Cards gleichmäßig
- Tabellen: volle Breite im Content-Bereich
- Kein willkürliches Nesting über 3 Ebenen

---

## Panel- und Card-Stil

```css
.panel {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 16px;
}

.panel-header {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #8b949e;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #21262d;
}
```

**Regeln:**
- Panels haben immer einen klaren Header
- Panels verwenden `border`, nicht nur `background`-Unterschied
- Subtile `box-shadow` erlaubt: `0 1px 3px rgba(0,0,0,0.3)`
- Kein übertriebenes Glow, kein Neon

---

## KPI-Cards

Verwendung auf: `index.html` (Übersicht), `countries/*.html`, `readiness.html`, `runs.html`

```
┌─────────────────────────┐
│  LABEL (UPPERCASE GREY) │
│  VALUE (groß, farbig)   │
│  delta / sub-label      │
└─────────────────────────┘
```

**Regeln:**
- KPI-Wert hat immer semantische Farbe (grün/amber/rot nach Band)
- Delta-Wert mit Pfeil-Icon und Farbe (positiv/negativ/neutral)
- Kein Glow-Effekt auf KPI-Werten — dezente Farbe reicht

---

## Status-Badges

Für Status S0–S6, Coverage-Bands, Freshness-Bands:

```css
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid currentColor;
}
```

**Regeln:**
- Immer Farbe + Border (kein reiner Hintergrund-Blob)
- Kurzer Code-Text (z.B. `S4`, `HIGH`, `STALE`) besser lesbar als langer Text
- Tooltip für vollständige Beschreibung wo sinnvoll

---

## Tabellen

```css
table {
  border-collapse: collapse;
  width: 100%;
}
th {
  background: #161b22;
  color: #8b949e;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 8px 12px;
  border-bottom: 2px solid #30363d;
  text-align: left;
}
td {
  padding: 8px 12px;
  border-bottom: 1px solid #21262d;
  font-size: 13px;
  color: #e6edf3;
}
tr:hover td {
  background: #1c2333;
}
```

**Regeln:**
- Zebra-Streifen vermeiden — `hover`-Highlight stattdessen
- Zahlen rechtsbündig ausrichten
- Statusfarben in `td` über semantische Klassen, nicht inline-styles

---

## Event- und Signal-Listen

Verwendet auf: `events.html`, Teile von `index.html`

- Kompakte Listenzeilen mit Timestamp + Quelle + Summary
- Prioritäts-Farbpunkt links (semantisch: rot/amber/blau/grau)
- Hover-Highlight
- Zeitstempel in gedämpftem Grau rechts

---

## Trends- und Chart-Panels

Die aktuelle Implementierung nutzt **Inline-SVG** (kein D3, kein Chart-Framework).

**Regeln:**
- SVG-Linien in `#388bfd` (blau) als Default
- Datenpunkte als kleine Kreise (`r=3`)
- Grid-Linien in `#21262d` sehr dezent
- Achsenbeschriftungen in `#8b949e`
- Keine 3D-Effekte, keine Pie-Charts
- Fehlende Daten-Segmente als gestrichelte Linie oder Lücke

---

## Validation / Backtest / Traceability-Ansichten

- **Validation:** Tabelle mit Testfällen, Pass/Fail-Badges, Score-Wert
- **Traceability:** Cluster-Tabelle mit Dependency-Badges, Origin-Labels
- **Backtest:** Zeitreihenvergleich mit Konfidenz-Band

**Regeln:**
- Technische Dichte ist erlaubt und gewünscht — keine Vereinfachung für "Laien"
- `<code>`-Blöcke für IDs und technische Bezeichner
- Faltbare Sektionen für sehr lange Artefaktlisten (mit `<details>/<summary>`)

---

## Zustände: Loading / Empty / Error

| Zustand | Visuelle Behandlung |
|---|---|
| Loading | Subtiler Shimmer-Effekt oder Text "Lade..." (kein Spinner ohne Funktion) |
| Empty | Zentiertes Panel mit Icon-Äquivalent + erläuterndem Text |
| Error | Rote Border + Error-Badge + technische Beschreibung in `<pre>` |
| Missing data | `—` (Gedankenstrich) mit Tooltip-Erklärung |

---

## Responsive-Verhalten

- **Primärziel:** Desktop 1280px+
- Minimal responsiv: bei < 768px sollten kritische Tabellen horizontal scrollbar sein (kein Brechen der Lesbarkeit)
- Keine aufwändige Mobile-Optimierung in V1 — das ist ein Analyse-Cockpit, kein Mobile-Produkt
- `overflow-x: auto` auf Tabellen-Containern

---

## Do / Don't

### ✅ Do

- Dunkle, ruhige Hintergründe mit klarer Panel-Struktur
- Semantische Farben für Statusindikatoren
- Klare Typografie-Hierarchie (H1 → H2 → H3 → Body)
- Inline-SVG für Datencharts (bestehendes Muster beibehalten)
- `html.escape()` auf allen dynamischen Inhalten
- Kleine, reviewbare Änderungsschritte
- Tests mitpflegen bei CSS-Klassenänderungen

### ❌ Don't

- Helle weiße Hintergründe auf primären Content-Flächen
- Neon-Glow-Effekte oder cyberpunk-Ästhetik
- Animationen ohne informationellen Zweck
- Externe CDN-Referenzen (Bootstrap, Tailwind, Google Fonts)
- Hardcodierte Inline-Colors auf `<td>`/`<span>` statt CSS-Klassen
- Framework-Migration (React, Vue, etc.) ohne explizite Freigabe
- Statusfarben umdefinieren ohne Readmodel-Prüfung
- Direktes Editieren von `build/local_gui/*.html`

---

*Erstellt: 2026-05-20 | Version: 1.0.0*
