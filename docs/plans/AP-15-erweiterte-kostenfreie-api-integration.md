# AP-15 — Erweiterte kostenfreie API-Integration

> Arbeitspaket: Integration von 8 verifizierten kostenfreien APIs zur Staerkung aller 5 SIASA-Domaenen
> Erstellt: 2026-06-24 | Status: Offen

---

## 1. Auftrag

Systematische Integration von 8 ausgewaehlten kostenfreien APIs in das SIASA-Fruehwarnsystem. Alle APIs wurden live verifiziert (AP-15 Recherche, 2026-06-24) und benoetigen keine Authentifizierung oder Registrierung.

### Ausgangslage
- 16 Adapter im System (nach AP-14)
- 36 aktive Signal-Keys
- Schwaechste Domain: C (Humanitaer) mit nur 3 Quellen
- Domain B hat Luecken durch blockierte UCDP/ReliefWeb-Adapter (AP-06)

### Ziel
- 8 neue Adapter implementiert und in Live-Runtime verdrahtet
- Domain C von 3 auf 6 Quellen gestaerkt (Gesundheit, Displacement, Ernaehrung)
- Domain E von 4 auf 6 Quellen gestaerkt (Internet-Outages, Zensur-Messungen)
- Domain D um globale IWF-Wirtschaftsdaten erweitert
- Domain B um Sanktionsdaten und humanitaere Konfliktereignisse erweitert

---

## 2. Ausgewaehlte APIs (8 von 16 Recherche-Kandidaten)

### Must-have (P1) — 6 Adapter

#### AP-15.1 — IMF SDMX Data API (Domain D)
```
URL: http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/{dataset}/{key}
Auth: keine | Rate: moderat | Format: SDMX-JSON
```
**Signale:** `imf_cpi_inflation`, `imf_gdp_growth`, `imf_commodity_oil_price`
**Begruendung:** World Bank liefert nur 2 jaehrliche Indikatoren. IMF liefert CPI-Inflation, BIP-Wachstum und Rohstoffpreise fuer 190+ Laender — schliesst die globale Makro-Luecke jenseits der EU (Eurostat).
**Verifiziert:** `CompactData/CPI/A.SDN.PCPI_PC_CP_A_PT` → Sudan-Inflationsdaten ✅

#### AP-15.2 — WHO GHO via Azure CDN (Domain C)
```
URL: https://ghoapi.azureedge.net/api/{IndicatorCode}
Auth: keine | Rate: moderat | Format: JSON (OData)
Hinweis: Haupt-API liefert HTTP 500, Azure CDN funktioniert stabil
```
**Signale:** `who_life_expectancy`, `who_under5_mortality`, `who_maternal_mortality`
**Begruendung:** Domain C hat keine Gesundheitsquelle. Lebenserwartung und Kindersterblichkeit sind etablierte Krisenindikatoren — Verschlechterung zeigt Systemversagen an.
**Verifiziert:** `WHOSIS_000001?$filter=SpatialDim eq 'SDN'` → Sudan-Daten ✅

#### AP-15.3 — IDMC Internal Displacement (Domain C)
```
URL: https://api.idmcdb.org/api/displacement_data
Auth: keine | Rate: unbegrenzt | Format: JSON (Liste)
```
**Signale:** `idmc_new_displacements_conflict`, `idmc_new_displacements_disaster`
**Begruendung:** UNHCR erfasst grenzueberschreitende Fluechtlinge. IDMC erfasst Binnenvertreibung — der weitaus groessere Teil der Vertriebenen weltweit. Schluesselindikator fuer interne Krisendynamik.
**Verifiziert:** `?iso3=UKR&year=2023` → Ukraine-Displacement-Daten ✅

#### AP-15.4 — IODA Internet Outage Detection (Domain E)
```
URL: https://api.ioda.inetintel.cc.gatech.edu/v2/
Auth: keine | Rate: moderat | Format: JSON
```
**Signale:** `ioda_outage_alert_count`, `ioda_bgp_visibility_drop`
**Begruendung:** Internet-Shutdowns korrelieren stark mit Konflikteeskalation, Repression und Wahlmanipulation. Einzige verfuegbare Echtzeit-Quelle fuer laenderbezogene Konnektivitaets-Ausfaelle.
**Verifiziert:** `/alerts?entityType=country&limit=5` → Alerts mit Laenderzuordnung ✅

#### AP-15.5 — OONI Censorship Measurements (Domain E)
```
URL: https://api.ooni.io/api/v1/
Auth: keine | Rate: moderat | Format: JSON
```
**Signale:** `ooni_blocked_site_count`, `ooni_censorship_incident_count`
**Begruendung:** Ergaenzt Voidly (berechneter Zensur-Score) um tatsaechliche Crowdsource-Messdaten aus 200+ Laendern. DNS-Manipulation und HTTP-Blocking sind direkte Indikatoren fuer Informationskontrolle.
**Verifiziert:** `/aggregation?probe_cc=IR&test_name=web_connectivity` → Iran-Zensurdaten ✅

#### AP-15.6 — FEWS NET Food Security (Domain C)
```
URL: https://fdw.fews.net/api/
Auth: keine | Rate: moderat | Format: JSON
Endpoints: marketpricefacts, foodsecurityoutlook, geographicunit
```
**Signale:** `fewsnet_food_price_index`, `fewsnet_ipc_phase`
**Begruendung:** FEWS NET ist der Gold-Standard fuer Ernaehrungssicherheits-Fruehwarnung. IPC-Phase 3+ bedeutet Krise, Phase 5 bedeutet Hungersnot. Deckt die 30 fraglichsten Laender ab — genau die, die SIASA ueberwacht.
**Verifiziert:** `/marketpricefacts/?format=json&country_code=ET` → Aethiopien-Marktpreise ✅

### Should-have (P2) — 2 Adapter

#### AP-15.7 — OpenSanctions (Domain B/D)
```
URL: https://api.opensanctions.org/
Auth: keine (Rate-Limited) | Format: JSON
```
**Signale:** `opensanctions_entity_count`, `opensanctions_new_listings`
**Begruendung:** Sanktionswellen korrelieren mit Konflikteeskalation. Zaehlung sanktionierter Entitaeten pro Land zeigt internationalen Druck und Isolierung an. Einzige kostenfreie Sanktionsdatenbank.
**Verifiziert:** `/search/sanctions?countries=ir&limit=10` → Iran-Sanktionsdaten ✅

#### AP-15.8 — HDX HAPI Humanitarian API (Domain B/C)
```
URL: https://hapi.humdata.org/api/v2/
Auth: app_identifier Parameter (beliebiger String, keine Registrierung)
```
**Signale:** `hdx_hapi_conflict_events`, `hdx_hapi_humanitarian_needs`, `hdx_hapi_funding_coverage`
**Begruendung:** Umfassendste humanitaere Datenquelle — Konfliktereignisse, Fluechtlingszahlen, humanitaere Bedarfe und Funding-Luecken in einem API-Zugang. Schliesst die ACLED/ReliefWeb-Luecke (AP-06) teilweise.
**Verifiziert:** `/food/food-security?location_code=SDN&app_identifier=siasa` → Sudan-Daten ✅

---

## 3. Nicht ausgewaehlt (mit Begruendung)

| API | Domain | Grund fuer Ausschluss |
|-----|--------|----------------------|
| NASA EONET | C | Ueberschneidung mit GDACS (bereits integriert) |
| USGS Earthquakes | C | Ueberschneidung mit GDACS |
| BIS Statistics | D | Ueberschneidung mit ECB fuer Eurozone; global nur Leitzinsen |
| ILO ILOSTAT | D | Ueberschneidung mit Eurostat (EU) und IMF (global) |
| UN Population | C | Nur alle 2 Jahre aktualisiert — zu langsam fuer Fruehwarnung |
| Wikidata SPARQL | A/B | Historisch wertvoll, nicht tagesaktuell |
| RIPE STAT | E | Zu technisch/nischig, IODA deckt Internet-Monitoring besser ab |
| Bluesky API | A | Zu geringe Nutzerbasis, GDELT + Wikipedia reichen |

---

## 4. Arbeitspakete (TAPs)

### Phase 1: P1-Adapter (AP-15.1 bis AP-15.6)

| TAP | Adapter | SwR | Geschaetzte Tests | Dateien |
|-----|---------|-----|-------------------|---------|
| AP-15.1 | IMF SDMX | SwR-076 | ~20 | `src/siasa/adapters/imf_sdmx.py`, `tests/unit/test_adapter_imf_sdmx.py` |
| AP-15.2 | WHO GHO | SwR-077 | ~20 | `src/siasa/adapters/who_gho.py`, `tests/unit/test_adapter_who_gho.py` |
| AP-15.3 | IDMC | SwR-078 | ~15 | `src/siasa/adapters/idmc_displacement.py`, `tests/unit/test_adapter_idmc.py` |
| AP-15.4 | IODA | SwR-079 | ~18 | `src/siasa/adapters/ioda_outages.py`, `tests/unit/test_adapter_ioda.py` |
| AP-15.5 | OONI | SwR-080 | ~18 | `src/siasa/adapters/ooni_censorship.py`, `tests/unit/test_adapter_ooni.py` |
| AP-15.6 | FEWS NET | SwR-081 | ~20 | `src/siasa/adapters/fewsnet.py`, `tests/unit/test_adapter_fewsnet.py` |

### Phase 2: P2-Adapter (AP-15.7 bis AP-15.8)

| TAP | Adapter | SwR | Geschaetzte Tests | Dateien |
|-----|---------|-----|-------------------|---------|
| AP-15.7 | OpenSanctions | SwR-082 | ~18 | `src/siasa/adapters/opensanctions.py`, `tests/unit/test_adapter_opensanctions.py` |
| AP-15.8 | HDX HAPI | SwR-083 | ~22 | `src/siasa/adapters/hdx_hapi.py`, `tests/unit/test_adapter_hdx_hapi.py` |

### Phase 3: Integration (AP-15.9 bis AP-15.11)

| TAP | Beschreibung |
|-----|-------------|
| AP-15.9 | Signal-Registry + Feature-Katalog + Quellkatalog Update |
| AP-15.10 | Live-Runtime-Verdrahtung aller 8 Adapter + Normalisierungs-Mappings |
| AP-15.11 | E2E-Integration-Tests (Pipeline-Durchlauf mit neuen Quellen) |

---

## 5. Dependency-Map

```
AP-15.1 (IMF) ─────────┐
AP-15.2 (WHO) ──────────┤
AP-15.3 (IDMC) ─────────┤
AP-15.4 (IODA) ─────────┤──→ AP-15.9 (Registry) ──→ AP-15.10 (Runtime) ──→ AP-15.11 (E2E)
AP-15.5 (OONI) ─────────┤
AP-15.6 (FEWS NET) ─────┘

AP-15.7 (OpenSanctions) ─┐
AP-15.8 (HDX HAPI) ──────┘──→ Registry/Runtime Update (inkrementell)
```

## 6. Erwartete Ergebnisse

| Metrik | Aktuell (nach AP-14) | Nach AP-15 |
|--------|---------------------|------------|
| Adapter total | 16 | 24 |
| Normalisierungs-Mappings | 16 | 24 |
| Aktive Signal-Keys | 36 | ~55 |
| Software Requirements | 75 | 83 |
| Domain B Quellen | 3 | 5 (+OpenSanctions, HDX HAPI) |
| Domain C Quellen | 3 | 7 (+WHO, IDMC, FEWS NET, HDX HAPI) |
| Domain D Quellen | 5 | 6 (+IMF) |
| Domain E Quellen | 4 | 6 (+IODA, OONI) |
| Geschaetzte neue Tests | 0 | ~150 |

## 7. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| WHO Azure-CDN instabil | niedrig | Retry + Fallback-Endpoint |
| IMF SDMX-Format komplex | mittel | ECB-Adapter-Pattern (AP-14.2) wiederverwenden |
| FEWS NET nur ~30 Laender | niedrig | Deckt genau die Krisenlaender ab die SIASA ueberwacht |
| OpenSanctions Rate-Limiting | mittel | Caching, Abfrage-Frequenz begrenzen |
| OONI Datenqualitaet variabel | mittel | Tagesaggregation statt Einzelmessungen |
| IODA API-Aenderungen | niedrig | Schema-Validierung im Adapter |

## 8. Neue Dependencies
Keine — alle APIs nutzen `urllib`/`json` (bereits vorhanden).

## 9. Abgrenzung

### In Scope
- 8 Adapter mit TDD (RED→GREEN→REFACTOR)
- V-Model-Chain pro Adapter (SwR + TC + Traces + Impl-Links)
- Signal-Registry + Feature-Katalog + Quellkatalog
- Live-Runtime-Verdrahtung
- E2E-Integration-Tests

### Explizit NICHT in Scope
- P3-APIs (USGS, UN Pop, Wikidata, RIPE, Bluesky)
- Kostenpflichtige APIs (AP-06)
- ML-Training auf neuen Signalen
- GUI-Erweiterungen (Sources-Seite zeigt neue Adapter automatisch)
- Historische Backfill-Pipelines
