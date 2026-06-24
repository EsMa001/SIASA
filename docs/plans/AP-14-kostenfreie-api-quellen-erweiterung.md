# AP-14 — Kostenfreie API-Quellen-Erweiterung (Recherche + Integration)

> Arbeitspaket: Recherche, Bewertung und Integration weiterer kostenfreier APIs
> Erstellt: 2026-06-24 | Status: Erledigt | Abgeschlossen: 2026-06-24

---

## 1. Motivation und Ziel

### Problem (Ausgangslage)
- **Domain A (Narrative):** Nur GDELT — keine alternativen Aufmerksamkeitsindikatoren
- **Domain B (Sicherheit):** GDELT Events + GDACS live; UCDP + ReliefWeb extern blockiert (AP-06)
- **Domain C (Humanitaer):** UNHCR + HDX-INFORM; keine Gesundheits-/Ernaehrungssicherheitssignale
- **Domain D (Wirtschaft):** World Bank (jaehrlich) + Frankfurter FX (taeglich) — nur 2 Quellen, keine Inflations-/Arbeitsmarktdaten
- **Domain E (Cyber):** CISA-KEV (global) + Voidly (Zensur) — keine Vulnerability-Trends

### Zielzustand (erreicht)
- 4 neue verifizierte Quellen integriert (Domain A, D, E erweitert)
- Alle Quellen kostenfrei, keine Authentifizierung erforderlich
- 17 neue Signal-Keys in der Registry (19 → 36 aktive Keys)
- Alle Adapter mit V-Model-Chain (SwR + TC + Traces), TDD, Live-Runtime verdrahtet

---

## 2. Recherche-Ergebnis: API-Bewertungsmatrix

### Verifiziert und integriert (P1)

| API | Domain | Auth | Laender | Update-Frequenz | Signale | Status |
|-----|--------|------|---------|-----------------|---------|--------|
| **Wikipedia Pageviews** | A | keine | global (via Topic) | taeglich | `wiki_pageview_count` | Integriert ✅ |
| **ECB Data API** | D | keine | Eurozone + 40 FX | taeglich | `ecb_key_rate`, `ecb_fx_{ccy}_per_eur` | Integriert ✅ |
| **Eurostat** | D | keine | EU-27 + Kandidaten | monatlich | `eurostat_hicp_inflation`, `eurostat_unemployment_rate` | Integriert ✅ |
| **NVD CVE 2.0** | E | keine (opt. Key) | global | taeglich | `nvd_cve_count_daily`, `nvd_avg_cvss_base`, `nvd_critical_cve_count` | Integriert ✅ |

### Bedingt integrierbar (P2 — API-Probleme bei Test)

| API | Domain | Auth | Problem | Potenzielle Signale | Status |
|-----|--------|------|---------|---------------------|--------|
| **ACLED** | B | unklar | Leere API-Antworten — vermutlich Registrierung noetig | `acled_event_count`, `acled_fatality_count`, `acled_protest_count` | Blockiert ⚠️ |
| **WHO GHO** | C | keine | HTTP 500 bei Test | `who_cholera_cases`, `who_immunization_rate` | Blockiert ⚠️ |

### Weitere evaluierte Kandidaten (P3 / verworfen)

| API | Domain | Ergebnis | Grund |
|-----|--------|----------|-------|
| **UNHCR API** | C | Bereits integriert | Bestehender Adapter deckt ab |
| **NASA FIRMS** | C | Needs Key | Kostenloser API-Key noetig, Registrierung |
| **OECD SDMX** | D | Komplex | SDMX-Syntax aufwaendig, nur OECD-37 |

### Nicht verifizierbar / blockiert

| API | Ergebnis | Grund |
|-----|----------|-------|
| **IPC Food Insecurity** | 404 | API-Endpoint veraltet/offline |
| **FRED (Fed Reserve)** | Key noetig | 32-Zeichen API-Key, Registrierung |
| **WTO** | Nicht erreichbar | API-Endpunkt antwortet nicht |
| **Statistics of World** | Leer | API v1+v2 liefern `data:[]` |

---

## 3. Detailbeschreibung der integrierten APIs

### 3.1 Wikipedia Pageviews API (Domain A — Narrative Attention)
```
URL: https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/all-agents/{article}/daily/{start}/{end}
Auth: keine
Rate: 100 req/s
Format: JSON
Historie: ab 2015
```
**Signal:** `wiki_pageview_count` — Taeglich Pageviews fuer laenderspezifische Wikipedia-Artikel.
Steigende Pageviews = steigende oeffentliche Aufmerksamkeit → fruehes Narrativ-Signal.
**Laender-Mapping:** Topic-basiert (englischer Laendername als Artikel-Titel).
**Adapter:** `src/siasa/adapters/wikipedia_pageviews.py` — WikipediaPageviewsAdapter
**SwR:** SwR-072 | **TC:** TC-SwR-072-001 | **Tests:** 26

### 3.2 ECB Statistical Data Warehouse (Domain D — Economic)
```
URL: https://data-api.ecb.europa.eu/service/data/{dataflow}/{key}?format=jsondata
Auth: keine
Rate: nicht dokumentiert (moderat)
Format: SDMX-JSON
Historie: ab 1999
```
**Signale:**
- `ecb_key_rate` — EZB-Hauptrefinanzierungszins (taeglich)
- `ecb_fx_{ccy}_per_eur` — Wechselkurse (USD, JPY, GBP, CHF, CNY, TRY, ZAR + weitere)
**Laender-Mapping:** Eurozone (20 Laender) bekommen Leitzins; alle Laender mit Waehrung bekommen FX.
**Adapter:** `src/siasa/adapters/ecb_data.py` — ECBDataAdapter
**SwR:** SwR-073 | **TC:** TC-SwR-073-001 | **Tests:** 23

### 3.3 Eurostat API (Domain D — Economic)
```
URL: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?geo={iso2}&format=JSON
Auth: keine
Rate: nicht dokumentiert
Format: JSON-stat
Historie: ab 1996
```
**Signale:**
- `eurostat_hicp_inflation` — Monatliche harmonisierte Verbraucherpreisinflation
- `eurostat_unemployment_rate` — Monatliche saisonbereinigte Arbeitslosenquote
**Laender-Mapping:** EU-27 + Kandidatenlaender (~35 Laender), ISO-2 ↔ ISO-3 Konversion.
**Adapter:** `src/siasa/adapters/eurostat.py` — EurostatAdapter
**SwR:** SwR-074 | **TC:** TC-SwR-074-001 | **Tests:** 21

### 3.4 NVD CVE 2.0 API (Domain E — Cyber)
```
URL: https://services.nvd.nist.gov/rest/json/cves/2.0?pubStartDate={start}&pubEndDate={end}
Auth: keine (optional API-Key fuer 50 statt 5 req/30s)
Rate: 5 req/30s
Format: JSON
Historie: ab 1999
```
**Signale:**
- `nvd_cve_count_daily` — Tagesanzahl neuer CVEs
- `nvd_avg_cvss_base` — Durchschnittlicher CVSS-Basiswert
- `nvd_critical_cve_count` — Anzahl CRITICAL-Schwere CVEs
**Laender-Mapping:** Global (country_id = "GLOBAL") — CVEs sind nicht laenderspezifisch.
**Adapter:** `src/siasa/adapters/nvd_cve.py` — NVDCVEAdapter
**SwR:** SwR-075 | **TC:** TC-SwR-075-001 | **Tests:** 21

---

## 4. Arbeitspakete (TAPs) — Umsetzungshistorie

### Phase 1: Adapter-Implementierung (AP-14.1 bis AP-14.4)

| TAP | Beschreibung | SwR | Tests | Commit | Status |
|-----|-------------|-----|-------|--------|--------|
| AP-14.1 | Wikipedia Pageviews Adapter | SwR-072 | 26 | `a16c91f` | Erledigt ✅ |
| AP-14.2 | ECB Data Adapter (SDMX-JSON) | SwR-073 | 23 | `bdfa09d` | Erledigt ✅ |
| AP-14.3 | Eurostat Adapter (JSON-stat) | SwR-074 | 21 | `9d34056` | Erledigt ✅ |
| AP-14.4 | NVD CVE 2.0 Adapter | SwR-075 | 21 | `5238a33` | Erledigt ✅ |

### Phase 2: Katalog + Registry (AP-14.5)

| TAP | Beschreibung | Aenderungen | Commit | Status |
|-----|-------------|-------------|--------|--------|
| AP-14.5 | Signal-Registry + Feature-Katalog + Masterplan | Registry: 19→36 Keys; Katalog: +7 Features | `dbb80c2` | Erledigt ✅ |

### Phase 3: Runtime-Integration (AP-14.6)

| TAP | Beschreibung | Aenderungen | Commit | Status |
|-----|-------------|-------------|--------|--------|
| AP-14.6 | Live-Runtime-Verdrahtung + Normalisierungs-Mappings + Quellkatalog | 4 Adapter-Instanzen, 16 Mappings, data_sources.yaml | `e45e76c` | Erledigt ✅ |

### Integrations-Fix

| TAP | Beschreibung | Aenderungen | Commit | Status |
|-----|-------------|-------------|--------|--------|
| Fix | Traceability-Konsistenz (Count-Bumps, Slice-Assertions) | test_specifications.yaml verifies→requirement_ids; Counts 71→75; Slice 10→11 | `76a4f74` | Erledigt ✅ |

### Bedingte TAPs (offen)

| TAP | Beschreibung | Blocker | Status |
|-----|-------------|---------|--------|
| AP-14.P2a | ACLED Adapter (Domain B) | API-Zugang unklar (leere Antworten) | Blockiert ⚠️ |
| AP-14.P2b | WHO GHO Adapter (Domain C) | API-Server HTTP 500 | Blockiert ⚠️ |

---

## 5. Dependency-Map

```
AP-14.1 (Wikipedia) ──┐
AP-14.2 (ECB) ────────┤──→ AP-14.5 (Registry/Katalog) ──→ AP-14.6 (Runtime)
AP-14.3 (Eurostat) ───┤                                          │
AP-14.4 (NVD CVE) ────┘                                     76a4f74 (Fix)

AP-14.P2a (ACLED) ──────── blockiert (extern)
AP-14.P2b (WHO) ─────────── blockiert (API-Stabilitaet)
```

## 6. Neue Dependencies (pyproject.toml)
Keine — alle APIs nutzen `urllib`/`json` (bereits vorhanden). Kein neues Paket noetig.

## 7. Metriken

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| Adapter total | 12 | 16 |
| Normalisierungs-Mappings | 12 | 16 |
| Aktive Signal-Keys | 19 | 36 |
| Software Requirements (SwR) | 71 | 75 |
| Traceability-Slices | 10 | 11 |
| Feature-Katalog-Eintraege | — | +7 |
| Neue Unit-Tests | 0 | 91 |
| Unit-Tests total (excl. env-dep.) | ~700 | 793+ |
| SwR ohne TC | 17 | 0 (Fix: verifies→requirement_ids) |

## 8. Risiken und Mitigationen

| Risiko | Eingetreten? | Mitigation |
|--------|-------------|------------|
| API-Rate-Limits bei NVD | Nein | Optional API-Key registrieren (kostenlos) |
| Eurostat-API-Format-Aenderungen | Nein | Schema-Validierung im Adapter |
| Wikipedia-Pageviews als Proxy ungenau | N/A | Nur Ergaenzungssignal, nicht primaer |
| ECB SDMX-Format komplex | Nein | SDMX-JSON erfolgreich geparst |
| ACLED-Zugang bleibt unklar | Ja | Als P2 geparkt; Domain B hat 3 andere Quellen |
| WHO-API instabil | Ja | Als P2 geparkt; Domain C hat UNHCR + HDX-INFORM |

## 9. Abgrenzung

### In Scope (erledigt)
- 4 verifizierte P1-Adapter mit TDD (SwR-072..075)
- Signal-Registry-Erweiterung (17 neue Keys)
- Feature-Katalog-Erweiterung (7 analytische Features)
- Live-Runtime-Verdrahtung (16 Adapter, 16 Mappings)
- Quellkatalog-Aktualisierung (4 neue Live/Core-Eintraege)
- V-Model-Chain komplett (SwR + TC + trace_links + impl_links)
- Fix: test_specifications verifies→requirement_ids (18 TCs migriert)

### Explizit NICHT in Scope
- Kostenpflichtige APIs (bleiben in AP-06)
- ML-Model-Training auf neuen Signalen (separates AP)
- GUI-Erweiterung fuer neue Quellen-Steckbriefe (Sources-Seite zeigt automatisch)
- Historische Backfill-Pipelines
- ACLED/WHO-Integration (blockiert, P2)

---

## 10. V-Model Traceability

| Artefakt | IDs |
|----------|-----|
| Software Requirements | SwR-072, SwR-073, SwR-074, SwR-075 |
| Test Cases | TC-SwR-072-001, TC-SwR-073-001, TC-SwR-074-001, TC-SwR-075-001 |
| Traceability Slice | `ap-14-kostenfreie-api-quellen` |
| derives_from | SyR-006, SyR-007 |
| allocated_to | DDS-001 |

## 11. Commit-Historie

| Commit | Beschreibung |
|--------|-------------|
| `057e84b` | Recherche + Detailplan |
| `a16c91f` | AP-14.1: Wikipedia Pageviews (26 Tests) |
| `bdfa09d` | AP-14.2: ECB Data (23 Tests) |
| `9d34056` | AP-14.3: Eurostat (21 Tests) |
| `5238a33` | AP-14.4: NVD CVE (21 Tests) |
| `dbb80c2` | AP-14.5: Registry + Katalog + Masterplan |
| `e45e76c` | AP-14.6: Runtime-Verdrahtung + Quellkatalog |
| `76a4f74` | Fix: Traceability-Konsistenz |
