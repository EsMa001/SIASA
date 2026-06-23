# AP-13 — ML-Training Data Lake

> Grosses Arbeitspaket: Dauerhafte, ML-optimierte Datenhaltung fuer alle SIASA-Domaenen
> Erstellt: 2026-06-23 | Status: Entwurf (noch nicht umgesetzt)

---

## 1. Motivation und Ziel

### Problem heute
- SQLite-Storage hat **168h Retention** (7 Tage) — historische Daten gehen verloren
- `historical_records`-Tabelle speichert nur kurzfristige Operational-Snapshots
- Kein langfristiges Archiv fuer ML-Training
- Keine standardisierte Feature-Aufbereitung fuer Zeitreihen-Modelle
- Keine Datenversionierung

### Zielzustand
- **Permanentes Parquet-Archiv** mit allen Rohdaten seit Projektstart
- **Taeglich alignierter Feature-Store** mit Multi-Resolution-Support
- **ML-ready Training-Datensaetze** (PyTorch DataLoader / HuggingFace Datasets kompatibel)
- **Reproduzierbare Datenversionierung** mit DVC
- Skalierbar auf Jahre (Projektion: ~3 GB/Jahr komprimiert, ~30 GB in 10 Jahren)

---

## 2. Technologie-Entscheidungen (Recherche-Ergebnis)

### 2.1 Speicher-Architektur: Dual-Storage

```
┌─────────────────────────────────────────────────────────────────┐
│                     SIASA Daten-Architektur                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SQLite (BEHALTEN)              Parquet Data Lake (NEU)         │
│  ══════════════════             ═══════════════════════         │
│  - Operational State            - Permanentes Archiv            │
│  - Runs, Scores, 168h           - Alle Records seit Start      │
│  - Latest-Bundle Mgmt           - ML-optimiertes Layout        │
│  - Governance/Release            - DVC-versioniert              │
│                                                                 │
│         │                              │                        │
│         │  Schreib-Pipeline            │  Lese-Pipeline          │
│         ▼                              ▼                        │
│  ┌─────────────┐              ┌──────────────────┐             │
│  │ storage.py  │              │  DuckDB Engine    │             │
│  │ (operational)│             │  (analytisch)     │             │
│  └─────────────┘              │  Zero-Copy Arrow  │             │
│                               │  → PyTorch/HF     │             │
│                               └──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

**Begruendung:**
- SQLite bleibt fuer Operational State (runs, scores, governance) — bewaehrt und stabil
- Parquet-Archiv NEU fuer langfristige Datenhaltung und ML-Training
- DuckDB als eingebettete Query-Engine ueber Parquet (Zero-Copy Arrow Output)
- Kein separater Datenbankserver noetig (single-machine, pip install)

### 2.2 Dateiformat: Apache Parquet

| Kriterium | Parquet | SQLite | JSONL | CSV | HDF5 |
|-----------|---------|--------|-------|-----|------|
| ML-Training (DataLoader) | ★★★★★ | ★★ | ★★★ | ★★ | ★★★★ |
| Kompression | 5-10:1 | 1:1 | 2:1 | 1:1 | 3-5:1 |
| Zeitfenster-Slicing | ★★★★★ | ★★★ | ★ | ★ | ★★★ |
| Schema-Evolution | ★★★★ | ★★★ | ★★★★★ | ★ | ★★★ |
| HuggingFace/pandas/polars | ★★★★★ | ★★★ | ★★★★ | ★★★ | ★★★ |
| Skalierbarkeit (TB) | ★★★★★ | ★★ | ★★★ | ★ | ★★★★ |
| Partitionierung | nativ | nein | manuell | nein | Gruppen |

**Begruendung:** Parquet ist der De-facto-Standard fuer ML-Daten (HuggingFace Default, PyTorch Integration, Arrow Zero-Copy). Kompression 5-10:1 haelt 10 Jahre Daten auf ~30 GB.

### 2.3 Query-Engine: DuckDB

- **Embedded** (pip install, kein Server)
- Liest Parquet direkt mit Predicate Pushdown (nur benoetigte Spalten/Partitionen laden)
- Arrow-Output direkt in PyTorch/TensorFlow ohne Kopieren
- SQL-Interface fuer ad-hoc Analysen
- Sweet Spot: <100 GB (SIASA passt perfekt)

### 2.4 Datenversionierung: DVC

- Git-Integration (`.dvc` Pointer-Dateien in Git, Daten in Remote)
- Pipeline-DAGs (`dvc.yaml`) fuer reproduzierbare Verarbeitung
- Remote Storage: lokal, S3, GCS, SSH
- Experiment-Tracking eingebaut
- Leichtgewichtig, Python-nativ

---

## 3. Datenmodell

### 3.1 Record-Schema (Archiv-Ebene)

Jeder archivierte Record hat folgendes Schema:

```python
@dataclass(frozen=True)
class ArchiveRecord:
    # === Identifikation ===
    record_id: str           # UUID oder deterministischer Hash
    source_id: str           # z.B. "SRC-GDELT-EVENTS", "WB-INDICATORS"
    country_id: str          # ISO-3 (z.B. "UKR", "DEU")
    domain: str              # A/B/C/D/E
    
    # === Signal ===
    signal_key: str          # z.B. "conflict_event_count", "gdp_growth"
    value: float             # Numerischer Wert
    
    # === Zeitstempel (Dual-Timestamp) ===
    timestamp_utc: str       # Canonical Timestamp (UTC, ISO 8601)
                             # = Beginn der Messperiode (left-aligned)
    period_start: str        # Beginn des Gueltigkeitszeitraums
    period_end: str          # Ende des Gueltigkeitszeitraums
    granularity: str         # "15min" | "hourly" | "daily" | "monthly" | "yearly"
    ingestion_utc: str       # Wann der Record ins System kam
    
    # === Provenienz ===
    run_id: str              # SIASA Run-ID
    mapping_id: str          # Normalisierungs-Mapping-ID
    mapping_version: str     # Mapping-Version
    
    # === Qualitaet ===
    freshness_hours: float   # Aktualitaet in Stunden
    quality_flag: str        # Source-spezifisches Qualitaetsmerkmal
    quality_context: dict    # Erweiterte Qualitaets-Metadaten
```

### 3.2 Zeitstempel-Konventionen

Regel: `timestamp_utc` ist IMMER der **Beginn** der Messperiode (left-aligned):

| Quelle | Granularity | timestamp_utc | period_start | period_end |
|--------|-------------|---------------|--------------|------------|
| GDELT Events (15min) | 15min | 2026-06-23T14:00:00Z | =timestamp | +15min |
| GDELT Doc (daily) | daily | 2026-06-23T00:00:00Z | =timestamp | +1day |
| GDACS (hourly) | hourly | 2026-06-23T14:00:00Z | =timestamp | +1hour |
| CISA-KEV (daily) | daily | 2026-06-23T00:00:00Z | =timestamp | +1day |
| Frankfurter (daily) | daily | 2026-06-23T00:00:00Z | =timestamp | +1day |
| Voidly (unregelmässig) | daily | 2026-06-23T00:00:00Z | =timestamp | +1day |
| World Bank (yearly) | yearly | 2025-01-01T00:00:00Z | =timestamp | 2025-12-31T23:59:59Z |
| UNHCR (yearly) | yearly | 2025-01-01T00:00:00Z | =timestamp | 2025-12-31T23:59:59Z |
| HDX-INFORM (yearly) | yearly | 2025-01-01T00:00:00Z | =timestamp | 2025-12-31T23:59:59Z |

### 3.3 Parquet-Layout (Hive-Partitioning)

```
data/
  archive/                          # Permanentes Rohdaten-Archiv
    source={source_id}/
      year={YYYY}/
        month={MM}/
          {source_id}_{YYYY}_{MM}.parquet
  
  features/                         # Aufbereitete Features
    daily/                          # Canonical Daily Resolution
      domain={A-E}/
        country={ISO3}/
          {domain}_{ISO3}_{YYYY}.parquet
    
    structural/                     # Jaehrliche Strukturdaten (forward-filled)
      country={ISO3}/
        structural_{ISO3}.parquet
    
    multi_resolution/               # Multi-Resolution Features
      fast/                         # Taegliche Signale
        {ISO3}_{YYYY}.parquet
      slow/                         # Monatliche Aggregate
        {ISO3}_{YYYY}.parquet
      structural/                   # Jaehrliche Basiswerte
        {ISO3}.parquet
  
  training/                         # Versionierte Training-Datensaetze
    v{version}/
      train.parquet
      val.parquet
      test.parquet
      metadata.json                 # Schema, Zeitraum, Feature-Liste, Splits
  
  registry/                         # Stammdaten
    country_registry.parquet        # Canonical Country-Mapping
    signal_registry.parquet         # Signal-Key Metadaten
    source_registry.parquet         # Source-Metadaten
```

### 3.4 Country-Registry

Zentrale Entitaets-Aufloesung fuer alle Quellen:

```python
@dataclass
class CountryRegistryEntry:
    canonical_id: str        # ISO-3 (Primary Key)
    iso2: str                # ISO-2
    iso_numeric: int         # ISO Numerisch
    name_en: str             # Englischer Name
    name_variants: list[str] # Alternative Schreibweisen
    gdelt_code: str          # GDELT-spezifischer Code
    worldbank_code: str      # World Bank Code
    unhcr_code: str          # UNHCR Code
    ucdp_country_id: int     # UCDP numerische ID
    region: str              # UN-Region
    subregion: str           # UN-Subregion
    income_group: str        # World Bank Income Group
    active_in_siasa: bool    # Aktuell aktiv im System
    governed_domains: list[str]  # Aktive Domaenen [A,B,C,D,E]
```

### 3.5 Signal-Registry

Metadaten fuer alle ~50 Signal-Keys:

```python
@dataclass
class SignalRegistryEntry:
    signal_key: str          # z.B. "conflict_event_count"
    domain: str              # A/B/C/D/E
    source_id: str           # Primaere Quelle
    description: str         # Menschenlesbare Beschreibung
    unit: str                # Einheit (count, ratio, score, USD, ...)
    value_range: tuple       # Erwarteter Wertebereich (min, max)
    native_granularity: str  # Native Zeitgranularitaet
    aggregation_method: str  # Wie auf daily aggregieren (sum/mean/max/last)
    encoding_hint: str       # ML-Encoding-Empfehlung
    is_count: bool           # Zaehlwert (int-like) vs. stetig
    is_ratio: bool           # Verhaeltniswert (0-1 oder 0-100)
    higher_is_worse: bool    # Semantische Richtung
```

---

## 4. Feature-Engineering Pipeline

### 4.1 Multi-Resolution Alignment

Drei Feature-Layer mit unterschiedlicher Zeitaufloesung:

```
Fast Layer (daily)
══════════════════
Quellen: GDELT (aggregiert von 15min), GDACS, CISA-KEV, Frankfurter, Voidly
Alignment: Direkt oder daily-Aggregation
Signale: ~30 taegliche Indikatoren

Slow Layer (monthly rolling)
════════════════════════════
Quellen: GDELT (30d rolling mean/std), GDACS (monthly event counts)
Alignment: Rolling Windows ueber Fast Layer
Signale: ~15 Trend-/Volatilitaets-Indikatoren

Structural Layer (yearly, forward-filled)
═════════════════════════════════════════
Quellen: World Bank, UNHCR, HDX-INFORM
Alignment: Forward-Fill (LOCF) auf daily
Signale: ~10 strukturelle Basis-Indikatoren
```

### 4.2 Aggregations-Regeln

| Source | Native Granularity | → Daily Aggregation |
|--------|-------------------|---------------------|
| GDELT Events (15min) | 15min | SUM(event_count), MAX(goldstein_negative), MEAN(avg_tone) |
| GDELT Doc (daily) | daily | SUM(article_count), direkt |
| GDACS (hourly) | hourly | COUNT(events), MAX(alert_level) |
| CISA-KEV (daily) | daily | Direkt (recent_count, overdue_count) |
| Frankfurter FX (daily) | daily | Direkt (fx_rate), STDEV(rolling_5d) |
| Voidly (unregelmässig) | daily | LAST(censorship_score) |
| World Bank (yearly) | yearly | FORWARD-FILL → daily constant |
| UNHCR (yearly) | yearly | FORWARD-FILL → daily constant |
| HDX-INFORM (yearly) | yearly | FORWARD-FILL → daily constant |

### 4.3 Point-in-Time Join (Anti-Look-Ahead-Bias)

```python
def point_in_time_join(
    entity_timestamps: pd.DataFrame,  # (country_id, date)
    feature_table: pd.DataFrame,       # (country_id, timestamp_utc, signal_key, value)
    max_staleness: timedelta = timedelta(days=365)
) -> pd.DataFrame:
    """
    Fuer jedes (country, date) den LETZTEN bekannten Wert
    jedes Features ziehen — strikt ohne Zukunftswissen.
    """
    # Nur Werte die VOR dem Abfrage-Zeitpunkt liegen
    # Maximal max_staleness alt
    ...
```

### 4.4 Derived Features (berechnet, nicht gespeichert)

```python
# Beispiele fuer abgeleitete Features (Phase 2+)
derived_features = {
    # Trends
    "gdelt_event_7d_trend": "rolling_mean(conflict_event_count, 7) / rolling_mean(conflict_event_count, 30)",
    "fx_volatility_5d": "rolling_std(fx_rate, 5)",
    
    # Cross-Domain
    "security_economic_ratio": "conflict_event_count / gdp_growth",
    
    # Relative
    "gdelt_z_score": "(conflict_event_count - rolling_mean(30)) / rolling_std(30)",
    
    # Lagged
    "conflict_lag_7d": "shift(conflict_event_count, 7)",
}
```

---

## 5. ML-Training Integration

### 5.1 PyTorch DataLoader

```python
class SIASATimeSeriesDataset(torch.utils.data.Dataset):
    """
    Laedt Zeitfenster aus Parquet via DuckDB.
    Zero-Copy Arrow → Tensor Konvertierung.
    """
    def __init__(
        self,
        parquet_path: str,
        window_size: int = 90,        # Tage Lookback
        prediction_horizon: int = 7,   # Tage Vorhersage
        countries: list[str] | None = None,
        date_range: tuple[str, str] | None = None,
        features: list[str] | None = None,
    ):
        self.con = duckdb.connect()
        self.data = self._load_and_pivot(parquet_path, countries, date_range, features)
    
    def __getitem__(self, idx) -> tuple[torch.Tensor, torch.Tensor]:
        # window: (window_size, num_features) → input
        # target: (prediction_horizon, num_targets) → label
        ...
    
    def __len__(self) -> int:
        ...
```

### 5.2 HuggingFace Datasets

```python
from datasets import Dataset

# Direkt aus Parquet laden
ds = Dataset.from_parquet("data/training/v1/train.parquet")

# Mit DuckDB-Query
ds = Dataset.from_dict(
    duckdb.sql("""
        SELECT * FROM 'data/features/daily/**/*.parquet'
        WHERE country_id = 'UKR' AND domain = 'A'
    """).arrow()
)
```

### 5.3 Encoding-Strategien

| Feature-Typ | Tree-Models (XGBoost) | Deep Learning (Transformer) |
|-------------|----------------------|----------------------------|
| country_id (90) | Structural Features als Proxy | Trainable Embedding (dim=32) |
| domain (5) | One-Hot | One-Hot oder Embedding (dim=8) |
| signal_key (~50) | Pivotieren zu Spalten | Pivotieren zu Spalten |
| event_type | Hierarchisch + Goldstein | Multi-Level Embedding |
| quality_flag | Ordinal (0-2) | Ordinal (0-2) |

---

## 6. Arbeitspakete (Teilarbeitspakete / TAPs)

### Phase 1: Archiv-Infrastruktur (AP-13.1 bis AP-13.5)

#### AP-13.1 — Parquet-Schreiber im Run-Pipeline
**Scope:** Nach jedem SIASA-Run automatisch alle NormalizedRecords als Parquet archivieren
**Aenderungen:**
- `src/siasa/data/archive.py` (NEU): `ArchiveWriter` Klasse
- `src/siasa/runs/live_runtime.py`: Archive-Hook nach Normalisierung
- `pyproject.toml`: `pyarrow>=14.0` als Dependency
**Tests:** Archive-Writer unit tests, Parquet-Schema-Validierung, Round-Trip-Test
**Abhaengigkeiten:** Keine (kann sofort starten)

#### AP-13.2 — Country-Registry und Signal-Registry
**Scope:** Zentrale Stammdaten-Dateien als Parquet + YAML
**Aenderungen:**
- `data/registry/country_registry.parquet` + `country_registry.yaml` (NEU)
- `data/registry/signal_registry.parquet` + `signal_registry.yaml` (NEU)
- `data/registry/source_registry.yaml` (NEU)
- `src/siasa/data/registry.py` (NEU): Lade- und Validierungsfunktionen
- Bestehende Adapter: Source-spezifische Country-Mappings extrahieren und zentralisieren
**Tests:** Registry-Validierung, Vollstaendigkeit (alle aktiven ISO3 abgedeckt), Konsistenz
**Abhaengigkeiten:** Keine

#### AP-13.3 — Dual-Timestamp-Schema
**Scope:** Erweiterte Zeitstempel auf allen Records
**Aenderungen:**
- `src/siasa/data/normalization.py`: `period_start`, `period_end`, `granularity` zu NormalizedRecord
- Alle Adapter: Native Granularity korrekt setzen
- `src/siasa/data/archive.py`: Timestamps in Parquet-Schema
**Tests:** Timestamp-Konsistenz pro Adapter, Period-Validierung
**Abhaengigkeiten:** AP-13.1

#### AP-13.4 — DuckDB Query-Layer
**Scope:** Analytische Query-Engine ueber Parquet-Archiv
**Aenderungen:**
- `src/siasa/data/query.py` (NEU): `ArchiveQueryEngine`
  - Zeitfenster-Queries
  - Country/Domain-Filter
  - Aggregationen
  - Arrow-Output fuer ML
- `pyproject.toml`: `duckdb>=0.9` als Dependency
**Tests:** Query-Korrektheit, Predicate Pushdown, Arrow-Output-Validierung
**Abhaengigkeiten:** AP-13.1

#### AP-13.5 — DVC-Setup und Versionierung
**Scope:** Datenversionierung einrichten
**Aenderungen:**
- `dvc init` im Repo
- `dvc.yaml`: Pipeline-Definition (Ingest → Archive → Features → Training)
- `.dvc/` Konfiguration
- `data/.gitignore` + `.dvc` Pointer-Dateien
- `pyproject.toml`: `dvc` als Dev-Dependency
**Tests:** DVC-Pipeline reproduzierbar, Pointer-Dateien konsistent
**Abhaengigkeiten:** AP-13.1

### Phase 2: Feature-Engineering (AP-13.6 bis AP-13.9)

#### AP-13.6 — Daily Alignment Pipeline
**Scope:** Alle Records auf daily canonical resolution alignieren
**Aenderungen:**
- `src/siasa/features/alignment.py` (NEU): `DailyAligner`
  - Aggregation nach Signal-Registry Regeln (SUM/MEAN/MAX/LAST)
  - Forward-Fill fuer jaehrliche Daten
  - Gap-Detection und -Reporting
- `src/siasa/features/` (NEU Paket)
**Tests:** Aggregation-Korrektheit pro Source-Typ, Forward-Fill-Verhalten, Gap-Detection
**Abhaengigkeiten:** AP-13.1, AP-13.2, AP-13.3

#### AP-13.7 — Multi-Resolution Feature-Builder
**Scope:** Fast/Slow/Structural Layer aufbauen
**Aenderungen:**
- `src/siasa/features/multi_resolution.py` (NEU):
  - Fast Layer: Taegliche Signale (direkt aus Alignment)
  - Slow Layer: Rolling-Window Aggregate (7d, 30d, 90d mean/std/trend)
  - Structural Layer: Jaehrliche Basiswerte (forward-filled)
- Output: Multi-Resolution Parquet pro Country
**Tests:** Layer-Korrektheit, Rolling-Window-Mathematik, Layer-Konsistenz
**Abhaengigkeiten:** AP-13.6

#### AP-13.8 — Point-in-Time Join Engine
**Scope:** Look-Ahead-Bias-freie Feature-Zusammenstellung
**Aenderungen:**
- `src/siasa/features/pit_join.py` (NEU): Point-in-Time Join
  - Fuer jedes (country, date) letzten bekannten Wert ziehen
  - Staleness-Limits konfigurierbar
  - Fehlende Werte explizit kennzeichnen
**Tests:** Anti-Leakage-Verifikation, Staleness-Limits, Missing-Value-Handling
**Abhaengigkeiten:** AP-13.7

#### AP-13.9 — Training-Set Builder
**Scope:** Versionierte, ML-ready Training-Datensaetze erzeugen
**Aenderungen:**
- `src/siasa/features/training_builder.py` (NEU):
  - Train/Val/Test Split (temporal, nicht random!)
  - Pivotierung: Signal-Keys → Spalten
  - Normalisierung (z-Score, Min-Max) mit gespeicherten Parametern
  - metadata.json mit vollstaendiger Provenienz
- CLI: `python -m siasa.features.build_training_set --version v1 --date-range ...`
**Tests:** Split-Korrektheit (kein Temporal Leakage), Schema-Konsistenz, Reproduzierbarkeit
**Abhaengigkeiten:** AP-13.8

### Phase 3: ML-Integration (AP-13.10 bis AP-13.12)

#### AP-13.10 — PyTorch Dataset-Klasse
**Scope:** Nativer PyTorch DataLoader fuer SIASA-Zeitreihen
**Aenderungen:**
- `src/siasa/ml/datasets.py` (NEU): `SIASATimeSeriesDataset`
  - Konfigurierbares Zeitfenster (Lookback + Horizon)
  - Zero-Copy Arrow → Tensor
  - Batch-Collation fuer variable-length Sequenzen
- `pyproject.toml`: `torch` als optionale Dependency
**Tests:** Dataset-Output-Shape, Batch-Collation, Memory-Effizienz
**Abhaengigkeiten:** AP-13.9

#### AP-13.11 — HuggingFace Datasets Export
**Scope:** SIASA-Daten als HuggingFace Dataset publishen (lokal oder Hub)
**Aenderungen:**
- `src/siasa/ml/hf_export.py` (NEU): HuggingFace-kompatibler Export
  - Dataset Card mit Beschreibung, Schema, Lizenz
  - Push zu HuggingFace Hub (optional)
- `pyproject.toml`: `datasets` als optionale Dependency
**Tests:** HF-Dataset Lade-Test, Schema-Validierung
**Abhaengigkeiten:** AP-13.9

#### AP-13.12 — Encoding-Utilities
**Scope:** ML-Encoding fuer kategorische SIASA-Features
**Aenderungen:**
- `src/siasa/ml/encoding.py` (NEU):
  - Country Embeddings (Lookup-Tabelle mit Structural Features)
  - Event-Type hierarchisches Encoding
  - Domain One-Hot
  - Signal-Key Pivotierung
  - Quality-Flag Ordinal
**Tests:** Encoding-Round-Trip, Dimension-Korrektheit, Edge-Cases
**Abhaengigkeiten:** AP-13.2

### Phase 4: Operationalisierung (AP-13.13 bis AP-13.15)

#### AP-13.13 — Retention-Policy Migration
**Scope:** SQLite Retention (168h) beibehalten, aber Archiv-Schreiber garantiert dass ALLE Daten vorher nach Parquet archiviert sind
**Aenderungen:**
- `src/siasa/data/storage.py`: Pre-Cleanup Archive-Hook
- Garantie: Kein Record wird aus SQLite geloescht bevor es im Parquet-Archiv liegt
**Tests:** Retention-Hook-Verifikation, Daten-Vollstaendigkeits-Check
**Abhaengigkeiten:** AP-13.1

#### AP-13.14 — Archive Health Dashboard
**Scope:** Monitoring des Archiv-Zustands in der SIASA GUI
**Aenderungen:**
- `src/siasa/gui/local_app.py`: Neue `archive.html` Seite
  - Records-Count pro Source/Domain/Year
  - Speicherverbrauch
  - Letzte Archivierung
  - Gaps/Missing Data Heatmap
**Tests:** GUI-Rendering, Daten-Korrektheit
**Abhaengigkeiten:** AP-13.1, AP-13.4

#### AP-13.15 — CLI fuer Archive-Management
**Scope:** Kommandozeilen-Tools fuer Archiv-Verwaltung
**Aenderungen:**
- `scripts/archive_manager.py` (NEU):
  - `--stats`: Archiv-Statistiken
  - `--compact`: Kleine Parquet-Files zusammenfuegen
  - `--validate`: Schema + Daten-Integritaet pruefen
  - `--export-training`: Training-Set generieren
  - `--backfill`: Historische Daten nachtraeglich archivieren
**Tests:** CLI-Smoke-Tests, Compaction-Korrektheit
**Abhaengigkeiten:** AP-13.1, AP-13.4

---

## 7. Dependency-Map

```
AP-13.1 (Parquet Writer) ──┬──→ AP-13.3 (Timestamps) ──→ AP-13.6 (Daily Align) ──→ AP-13.7 (Multi-Res)
                           │                                                             │
AP-13.2 (Registries) ─────┤──→ AP-13.12 (Encoding)                                      │
                           │                                                             ▼
                           ├──→ AP-13.4 (DuckDB) ──→ AP-13.14 (Dashboard)        AP-13.8 (PIT Join)
                           │                                                             │
                           ├──→ AP-13.5 (DVC)                                            ▼
                           │                                                      AP-13.9 (Training Builder)
                           ├──→ AP-13.13 (Retention)                                     │
                           │                                                      ┌──────┼──────┐
                           └──→ AP-13.15 (CLI)                                    │      │      │
                                                                           AP-13.10  AP-13.11  (Encoding)
                                                                           (PyTorch)  (HF)
```

### Kritischer Pfad:
**AP-13.1 → AP-13.3 → AP-13.6 → AP-13.7 → AP-13.8 → AP-13.9 → AP-13.10**

### Parallel moeglich:
- AP-13.1 + AP-13.2 (keine Abhaengigkeit)
- AP-13.4 + AP-13.5 (beide nur von AP-13.1 abhaengig)
- AP-13.10 + AP-13.11 + AP-13.12 (nach AP-13.9)

---

## 8. Neue Dependencies

```toml
# pyproject.toml Erweiterungen
[project]
dependencies = [
    # ... bestehende ...
    "pyarrow>=14.0",        # Parquet I/O + Arrow
    "duckdb>=0.9",          # Eingebettete analytische Query-Engine
]

[project.optional-dependencies]
ml = [
    "torch>=2.0",           # PyTorch DataLoader
    "datasets>=2.14",       # HuggingFace Datasets
    "polars>=0.19",         # Schnelle DataFrame-Operationen
]
versioning = [
    "dvc>=3.0",             # Data Version Control
]
registry = [
    "pycountry>=22.3",      # ISO-3166 Country Lookup
]
```

---

## 9. Speicher-Projektion

| Zeitraum | Unkomprimiert | Parquet (komprimiert) | Records (geschaetzt) |
|----------|---------------|----------------------|---------------------|
| 1 Monat | ~1.2 GB | ~250 MB | ~6.6 Mio |
| 1 Jahr | ~14.7 GB | ~3 GB | ~79 Mio |
| 5 Jahre | ~73.5 GB | ~15 GB | ~395 Mio |
| 10 Jahre | ~147 GB | ~30 GB | ~790 Mio |

Berechnung: 90 Laender × 12 source_ids × ~50 signals × (15min-Export fuer GDELT, daily fuer Rest) × 365 Tage

---

## 10. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Parquet-Schema-Drift bei neuen Adaptern | Hoch | Mittel | Schema-Registry + Validierung bei jedem Write |
| DuckDB-Version-Inkompatibilitaet | Niedrig | Niedrig | Parquet ist format-stabil, DuckDB austauschbar |
| Speicherplatz bei langem Betrieb | Niedrig | Niedrig | 30 GB in 10 Jahren, Compaction-Tool |
| Temporal Leakage in Training-Sets | Mittel | Hoch | Temporal Split erzwingen, Anti-Leakage-Tests |
| Forward-Fill maskiert echte Datenlücken | Mittel | Mittel | Gap-Detection + explizites Missing-Tracking |
| DVC-Konflikte bei mehreren Hermes-Instanzen | Mittel | Mittel | Single-Writer-Pattern, Lock-Files |
| PyArrow/DuckDB Breaking Changes | Niedrig | Mittel | Version-Pinning, Parquet als stabiles Format |

---

## 11. Abgrenzung

### In Scope:
- Permanente Datenhaltung aller SIASA-Adapter-Outputs
- Feature-Engineering Pipeline fuer ML-Training
- PyTorch/HuggingFace Integration
- Datenversionierung

### Explizit NICHT in Scope:
- Model-Training selbst (eigenes AP)
- Online-Serving / Real-Time-Inference (spaeteres AP)
- Cluster/Cloud-Deployment (aktuell single-machine)
- Neue Datenquellen (AP-06 / AP-11 Bereich)
- GUI-Redesign (eigenes AP)

---

## 12. V-Model Traceability Vorbereitung

Dieses AP wird bei Umsetzung folgende V-Model-Artefakte benoetigen:
- **SyR**: Neues System Requirement fuer persistente Datenhaltung
- **SwR**: ~15 neue Software Requirements (pro TAP mind. 1)
- **TC**: Testspezifikationen fuer alle neuen Module
- **Trace-Links**: Durchgaengige Kette StR → SyR → SwR → TC → Code

Voraussichtliche StR-Zuordnung:
- StR-032 (Daten sollen langfristig archiviert werden) — FALLS vorhanden
- StR-xxx (ML-Training-Daten) — ggf. neues StR noetig
- StR-048 (Reproduzierbarkeit) — fuer DVC/Versionierung

---

*Dieses Dokument ist ein Planungsentwurf. Umsetzung erst nach Freigabe.*
