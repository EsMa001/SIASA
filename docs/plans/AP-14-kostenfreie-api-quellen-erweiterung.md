# AP-14 — Kostenfreie API-Quellen-Erweiterung (Recherche + Integration)

> Arbeitspaket: Recherche, Bewertung und Integration weiterer kostenfreier APIs
> Erstellt: 2026-06-24 | Status: Entwurf

---

## 1. Motivation und Ziel

### Problem heute
- **Domain A (Narrative):** Nur GDELT — keine Medien-Diversifikation, keine alternativen Aufmerksamkeitsindikatoren
- **Domain B (Sicherheit):** GDELT Events + GDACS live; UCDP + ReliefWeb extern blockiert — kein freier Zugang zu Gold-Standard-Konfliktdaten
- **Domain C (Humanitaer):** UNHCR + HDX-INFORM; ReliefWeb blockiert — keine Gesundheits-/Ernaehrungssicherheitssignale
- **Domain D (Wirtschaft):** World Bank (jaehrlich) + Frankfurter FX (taeglich) — nur 2 Quellen, keine Inflations-/Handels-/Energiedaten
- **Domain E (Cyber):** CISA-KEV (global, kein Laenderbezug) + Voidly (Zensur) — keine Vulnerability-Trends

### Zielzustand
- Mindestens **1 neue verifizierte Quelle pro Domain** integriert
- Alle Quellen **kostenfrei** (kein API-Key oder kostenloser Tier mit ausreichenden Limits)
- Jede Quelle mit **Laenderbezug** (kein rein globales Aggregat)
- Adapter folgen bestehendem Pattern (BaseAdapter → NormalizedRecord → Archive)

---

## 2. Recherche-Ergebnis: Verifizierte kostenfreie APIs

### Bewertungsmatrix

| API | Domain | Auth | Laender | Update | Verifiziert | Prioritaet | Signale |
|-----|--------|------|---------|--------|-------------|------------|---------|
| **Wikipedia Pageviews** | A | keine | global (via Topic) | taeglich | JA ✅ | P1 | Aufmerksamkeit/Salienz pro Land-Thema |
| **ECB Data API** | D | keine | Eurozone + global FX | taeglich | JA ✅ | P1 | Zinssaetze, Geldmenge, Wechselkurse (30+) |
| **Eurostat** | D | keine | EU-27 + Kandidaten | monatlich | JA ✅ | P1 | Inflation (HICP), Arbeitslosigkeit, Handel |
| **NVD CVE 2.0** | E | keine (optional Key) | global + Vendor-Mapping | taeglich | JA ✅ | P1 | CVE-Trends, CVSS-Schwere, Exploit-Praediktion |
| **ACLED** | B | unklar (leer) | 200+ | taeglich | UNKLAR ⚠️ | P2 | Konflikte, Proteste, Gewalt, Fatalities |
| **WHO GHO** | C | keine | 190+ | variiert | Server 500 ⚠️ | P2 | Krankheitsausbrueche, Gesundheitsindikatoren |
| **UNHCR API** | C | keine | global | jaehrlich | JA ✅ | P2 | Fluechtlinge, IDPs (erweitert bestehenden Adapter) |
| **NASA FIRMS** | C | API-Key (frei) | global | taeglich | Needs Key | P3 | Feuer/thermische Anomalien (Konflikt-Proxy) |
| **OECD SDMX** | D | keine | OECD-37 | monatlich | Syntax-komplex | P3 | CLI, BIP, Handel (nur OECD-Laender) |

### Nicht verifizierbar / blockiert (Stand 2026-06-24)
- **ACLED:** API liefert leere Antworten — moeglicherweise Registrierung noetig oder IP-blockiert
- **WHO GHO:** Server-Error 500 — temporaer oder API-Umbau
- **IPC Food Insecurity:** 404 — API-Endpoint veraltet
- **FRED:** Erfordert 32-Zeichen API-Key (keine freie Nutzung ohne Registrierung)
- **WTO:** API-Endpunkt nicht erreichbar

---

## 3. Priorisierte Integrationskandidaten (P1 — verifiziert + wertvoll)

### 3.1 Wikipedia Pageviews API (Domain A)
```
URL: https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/all-agents/{article}/daily/{start}/{end}
Auth: keine
Rate: 100 req/s (sehr grosszuegig)
Format: JSON
```
**Signal:** Taeglich Pageviews fuer laenderspezifische Wikipedia-Artikel (z.B. "Ukraine", "Syria", "Taiwan").
Steigende Pageviews = steigende oeffentliche Aufmerksamkeit/Salienz → fruehes Narrativ-Signal.
**Laender-Mapping:** Topic-basiert (Land-Name als Artikel-Titel, mehrere Sprachversionen aggregierbar)
**Wert:** Einziger kostenfreier Proxy fuer globale Aufmerksamkeits-Dynamik neben GDELT.

### 3.2 ECB Statistical Data Warehouse (Domain D)
```
URL: https://data-api.ecb.europa.eu/service/data/{dataflow}/{key}?format=jsondata
Auth: keine
Rate: nicht dokumentiert (moderat)
Format: JSON (SDMX)
```
**Signale:** 
- Taeglich: Wechselkurse (40+ Waehrungen), Zinssaetze
- Monatlich: Geldmengenaggregate (M1/M2/M3), Kreditvergabe
- Quartalsweise: BIP-Schaetzungen Eurozone
**Laender-Mapping:** Eurozone (20 Laender) + globale FX-Paare
**Wert:** Ergaenzt Frankfurter (nur FX) um Zins-/Geldmengensignale. Fruehindikator fuer wirtschaftliche Instabilitaet.

### 3.3 Eurostat API (Domain D)
```
URL: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?geo={iso2}&time={period}&format=JSON
Auth: keine
Rate: nicht dokumentiert
Format: JSON
```
**Signale:**
- Monatlich: HICP-Inflation pro EU-Land, Arbeitslosenquote, Industrieproduktion
- Quartalsweise: BIP-Wachstum, Handelsbilanzen
**Laender-Mapping:** EU-27 + UK + Kandidatenlaender (~35 Laender)
**Wert:** Einzige kostenfreie Quelle fuer monatliche Inflations- und Arbeitsmarktdaten auf Laenderebene.

### 3.4 NVD CVE 2.0 API (Domain E)
```
URL: https://services.nvd.nist.gov/rest/json/cves/2.0?pubStartDate={start}&pubEndDate={end}
Auth: keine (optional API-Key fuer hoehere Rate)
Rate: 5 req/30s (ohne Key), 50 req/30s (mit Key)
Format: JSON
```
**Signale:**
- Taeglich: Neue CVEs, CVSS-Scores (Base/Temporal), Exploitability
- Aggregierbar: CVE-Count-Trends, Schwere-Verteilung, betroffene Produktklassen
**Laender-Mapping:** Indirekt via CPE (Produkt → verbreitete Software pro Land/Sektor)
**Wert:** Ergaenzt CISA-KEV (nur exploitierte) um das volle Vulnerability-Spektrum. Trend-Analyse zeigt Cyber-Bedrohungslage.

---

## 4. Arbeitspakete (TAPs)

### Phase 1: Verifizierte P1-Adapter (AP-14.1 bis AP-14.4)

#### AP-14.1 — Wikipedia Pageviews Adapter (Domain A)
**Scope:** Taeglich Pageviews fuer konfigurierbare Laender-Topics abrufen
**Aenderungen:**
- `src/siasa/adapters/wikipedia_pageviews.py` (NEU)
- Signal: `wiki_pageview_count` (taeglich pro Land)
- Normalisierung: Raw-Count → NormalizedRecord
**Tests:** API-Response-Parsing, Laender-Mapping, Fehlerbehandlung
**Abhaengigkeiten:** Keine

#### AP-14.2 — ECB Data Adapter (Domain D)
**Scope:** Taeglich Wechselkurse + monatlich Zinssaetze aus ECB SDW
**Aenderungen:**
- `src/siasa/adapters/ecb_data.py` (NEU)
- Signale: `ecb_key_rate`, `ecb_m3_growth`, `ecb_fx_*`
- SDMX-JSON-Parsing
**Tests:** SDMX-Response-Parsing, Multi-Signal-Extraktion, Zeitreihen-Alignment
**Abhaengigkeiten:** Keine

#### AP-14.3 — Eurostat Adapter (Domain D)
**Scope:** Monatlich Inflation (HICP) + Arbeitslosenquote pro EU-Land
**Aenderungen:**
- `src/siasa/adapters/eurostat.py` (NEU)
- Signale: `eurostat_hicp_inflation`, `eurostat_unemployment_rate`
- Eurostat JSON-Stat-Parsing
**Tests:** JSON-Stat-Parsing, Laender-ISO-Mapping, Zeitraum-Extraktion
**Abhaengigkeiten:** Keine

#### AP-14.4 — NVD CVE Adapter (Domain E)
**Scope:** Taeglich neue CVEs + CVSS-Aggregation
**Aenderungen:**
- `src/siasa/adapters/nvd_cve.py` (NEU)
- Signale: `nvd_cve_count_daily`, `nvd_avg_cvss_base`, `nvd_critical_cve_count`
- Paginated API-Abruf, CVSS-Extraktion
**Tests:** CVE-Parsing, CVSS-Aggregation, Pagination, Rate-Limit-Handling
**Abhaengigkeiten:** Keine

### Phase 2: Bedingte P2-Adapter (AP-14.5 bis AP-14.7)

#### AP-14.5 — ACLED Adapter (Domain B) — bedingt
**Scope:** Falls Zugang klaerbar: Konfliktereignisse, Proteste, Fatalities pro Land
**Aenderungen:**
- `src/siasa/adapters/acled.py` (NEU)
- Signale: `acled_event_count`, `acled_fatality_count`, `acled_protest_count`
**Status:** Blockiert bis API-Zugang verifiziert
**Abhaengigkeiten:** Manuelle API-Zugangs-Klaerung

#### AP-14.6 — WHO GHO Adapter (Domain C) — bedingt
**Scope:** Falls API stabil: Gesundheitsindikatoren (Cholera, Malaria, Impfquoten)
**Aenderungen:**
- `src/siasa/adapters/who_gho.py` (NEU)
- Signale: `who_cholera_cases`, `who_immunization_rate`
**Status:** Blockiert bis API-Stabilitaet verifiziert
**Abhaengigkeiten:** API-Monitoring

#### AP-14.7 — Quellkatalog + Signal-Registry + Glossar Update
**Scope:** Alle neuen Adapter in Katalog, Signal-Registry und Glossar aufnehmen
**Aenderungen:**
- `vmodel/project/data_sources.yaml`: neue Core-Eintraege
- `data/registry/signal_registry.yaml`: neue Signale
- `docs/glossary.yaml`: neue Terme
**Tests:** Registry-Validierung, Vollstaendigkeits-Check
**Abhaengigkeiten:** AP-14.1 bis AP-14.4

### Phase 3: Runtime-Integration (AP-14.8)

#### AP-14.8 — Live-Runtime-Verdrahtung + Normalisierungs-Mappings
**Scope:** Neue Adapter in `live_runtime.py` verdrahten, Mappings definieren
**Aenderungen:**
- `src/siasa/runs/live_runtime.py`: Import + Adapter-Wiring
- `src/siasa/data/normalization_mappings.py`: Mapping-Eintraege
**Tests:** Runtime-Smoke-Test, Mapping-Korrektheit
**Abhaengigkeiten:** AP-14.1 bis AP-14.4

---

## 5. Dependency-Map

```
AP-14.1 (Wikipedia) ──┐
AP-14.2 (ECB) ────────┤──→ AP-14.7 (Katalog/Registry) ──→ AP-14.8 (Runtime)
AP-14.3 (Eurostat) ───┤
AP-14.4 (NVD CVE) ────┘
                         
AP-14.5 (ACLED) ───────── bedingt (extern)
AP-14.6 (WHO) ─────────── bedingt (API-Stabilitaet)
```

## 6. Neue Dependencies (pyproject.toml)
Keine — alle APIs nutzen `urllib`/`json` (bereits vorhanden). Kein neues Paket noetig.

## 7. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| API-Rate-Limits bei NVD | mittel | Optional API-Key registrieren (kostenlos) |
| Eurostat-API-Format-Aenderungen | niedrig | Schema-Validierung im Adapter |
| Wikipedia-Pageviews als Proxy ungenau | mittel | Nur als Ergaenzungssignal, nicht primaer |
| ECB SDMX-Format komplex | niedrig | Bewiesenes JSON-Format nutzen |
| ACLED-Zugang bleibt unklar | hoch | Als P2 geparkt; Domain B hat 3 andere Quellen |

## 8. Abgrenzung

### In Scope
- 4 verifizierte P1-Adapter + Katalog + Runtime-Integration
- Signal-Registry-Erweiterung
- Unit-Tests fuer jeden Adapter

### Explizit NICHT in Scope
- Kostenpflichtige APIs (bleiben in AP-06)
- ML-Model-Training auf neuen Signalen (separates AP)
- GUI-Erweiterung fuer neue Quellen (Quellen-Katalog-Seite zeigt automatisch)
- Historische Backfill-Pipelines (spaeter)

---

## 9. V-Model Traceability Vorbereitung
- Neue SyR fuer "erweiterte Quellen-Coverage" → StR-Anbindung an Stakeholder-Anforderungen
- Pro Adapter: 1 SwR + 1 TC + Trace-Links + Implementation-File-Links
- Signal-Registry muss nach jeder Adapter-Integration aktualisiert werden
