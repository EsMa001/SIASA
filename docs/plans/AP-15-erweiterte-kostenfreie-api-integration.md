# AP-15 — Erweiterte kostenfreie API-Integration (Recherche-Ergebnis + Integrationsplan)

> Arbeitspaket: Systematische Recherche und priorisierte Integration weiterer kostenfreier APIs
> Erstellt: 2026-06-24 | Status: Offen

---

## 1. Motivation und Ziel

### Ausgangslage nach AP-14
AP-14 hat 4 neue Adapter integriert (Wikipedia, ECB, Eurostat, NVD CVE). Damit stehen 16 Adapter zur Verfuegung. Es verbleiben jedoch signifikante Luecken:
- **Domain A (Narrative):** Nur GDELT + Wikipedia — keine Social-Media- oder strukturierte Wissenssignale
- **Domain B (Sicherheit):** GDELT Events + GDACS — UCDP/ReliefWeb blockiert; keine Sanktionsdaten
- **Domain C (Humanitaer):** UNHCR + HDX-INFORM — keine Gesundheits-, Ernaehrungs-, Displacement- oder Naturkatastrophendaten
- **Domain D (Wirtschaft):** World Bank + Frankfurter + ECB + Eurostat — keine IWF-, BIZ- oder Arbeitsmarktdaten
- **Domain E (Cyber):** CISA-KEV + Voidly + NVD CVE — keine Internet-Outage- oder Zensur-Messdaten

### Zielzustand
- Mindestens 8 neue Adapter aus den 16 verifizierten APIs integriert
- Alle 5 Domains signifikant gestaerkt
- Besonders Domain C (bisher am schwaechsten) mit 3+ neuen Quellen
- Alle Adapter kostenfrei, TDD, V-Model-Chain, Runtime-verdrahtet

---

## 2. Recherche-Ergebnis: 16 verifizierte kostenfreie APIs

### 2.1 Bewertungsmatrix — Alle verifizierten Kandidaten

| # | API | Domain | Auth | Laender | Update | Signale | Prioritaet |
|---|-----|--------|------|---------|--------|---------|------------|
| 1 | **IMF SDMX Data** | D | keine | 190+ | M/Q/A | CPI-Inflation, BIP-Wachstum, Rohstoffpreise | **P1** |
| 2 | **WHO GHO (Azure CDN)** | C | keine | 190+ | jaehrlich | Lebenserwartung, Kindersterblichkeit, Krankheitspravalenz | **P1** |
| 3 | **IDMC Displacement** | C | keine | global | jaehrlich | Neue Binnenvertreibungen (Konflikt + Katastrophen) | **P1** |
| 4 | **IODA Internet Outages** | E | keine | global | Echtzeit | Internet-Ausfaelle (BGP, Active Probing, Darknet) | **P1** |
| 5 | **OONI Censorship** | E | keine | 200+ | taeglich | Zensur-Messungen, DNS-Manipulation, HTTP-Blocking | **P1** |
| 6 | **FEWS NET Food Security** | C | keine | 30+ | M/Q | IPC-Phasen, Marktpreise, Ernaehrungslage | **P1** |
| 7 | **OpenSanctions** | B/D | keine (Rate-Limited) | global | taeglich | Sanktionierte Entitaeten pro Land, PEPs | **P2** |
| 8 | **HDX HAPI** | B/C | app_identifier (frei) | global | variiert | Konfliktereignisse, Fluechtlinge, Hum. Bedarfe, Funding | **P2** |
| 9 | **NASA EONET** | C | keine | global (Geo) | taeglich | Aktive Naturereignisse (Feuer, Vulkane, Stuerme) | **P2** |
| 10 | **BIS Statistics** | D | keine (SDMX) | 60+ | M/Q | Zentralbank-Leitzinsen, Kreditstatistiken | **P2** |
| 11 | **ILO ILOSTAT** | D | keine | 180+ | A/Q | Arbeitslosenquote, Erwerbsbeteiligung, Jugendarbeitslosigkeit | **P2** |
| 12 | **USGS Earthquakes** | C | keine | global (Geo) | Echtzeit | Erdbeben (Magnitude, Ort, Tiefe, Tsunami-Warnung) | **P3** |
| 13 | **UN Population Division** | C | keine | global | A/2-jaehrlich | Bevoelkerung, Fertilitaet, Migration, Altersstruktur | **P3** |
| 14 | **Wikidata SPARQL** | A/B | keine | global | laufend | Bewaffnete Konflikte, Putsche, Sanktionen (strukturiert) | **P3** |
| 15 | **RIPE STAT** | E | keine | global | Echtzeit | Internet-Infrastruktur, BGP-Sichtbarkeit, ASN-Metriken | **P3** |
| 16 | **Bluesky Public API** | A | keine | global (Text) | Echtzeit | Social-Media-Narrative zu Konflikten | **P3** |

### 2.2 API-Steckbriefe (P1-Kandidaten)

#### IMF SDMX Data API (Domain D)
```
URL: http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/{dataset}/{key}
Auth: keine
Rate: nicht dokumentiert (moderat)
Format: SDMX-JSON
Datasets: IFS (Finanzstatistik), WEO (World Economic Outlook), PCPS (Rohstoffpreise), BOP (Zahlungsbilanz)
```
**Signale:**
- `imf_cpi_inflation` — Jaehrliche CPI-Inflation pro Land (IFS)
- `imf_gdp_growth` — BIP-Wachstum real (WEO)
- `imf_commodity_oil_price` — Oelpreis-Index (PCPS)
**Wert:** Ergaenzt World Bank (nur 2 Indikatoren) und Eurostat (nur EU) um globale makrooekonomische Daten.
**Verifiziert:** `CompactData/CPI/A.SDN.PCPI_PC_CP_A_PT` → Daten fuer Sudan 2020-2023 ✅

#### WHO GHO via Azure CDN (Domain C)
```
URL: https://ghoapi.azureedge.net/api/{IndicatorCode}
Auth: keine
Rate: nicht dokumentiert
Format: JSON (OData)
Hinweis: Haupt-API (apps.who.int) liefert HTTP 500, Azure CDN funktioniert stabil
```
**Signale:**
- `who_life_expectancy` — Lebenserwartung bei Geburt (WHOSIS_000001)
- `who_under5_mortality` — Unter-5-Sterblichkeit (MDG_0000000001)
- `who_maternal_mortality` — Muettersterblichkeit
**Wert:** Einzige kostenfreie Quelle fuer laenderspezifische Gesundheitsindikatoren. Gesundheitsverschlechterung = fruehes Krisensignal.
**Verifiziert:** `WHOSIS_000001?$filter=SpatialDim eq 'SDN'` → Daten fuer Sudan ✅

#### IDMC Internal Displacement (Domain C)
```
URL: https://api.idmcdb.org/api/displacement_data
Auth: keine
Rate: nicht dokumentiert
Format: JSON (Liste)
```
**Signale:**
- `idmc_new_displacements_conflict` — Neue konfliktbedingte Binnenvertreibungen
- `idmc_new_displacements_disaster` — Neue katastrophenbedingte Binnenvertreibungen
**Wert:** Ergaenzt UNHCR (grenzueberschreitend) um Binnenvertreibung. Wichtigster Indikator fuer interne Krisendynamik.
**Verifiziert:** `?iso3=UKR&year=2023` → Daten fuer Ukraine 2023 ✅

#### IODA Internet Outages (Domain E)
```
URL: https://api.ioda.inetintel.cc.gatech.edu/v2/
Auth: keine
Rate: nicht dokumentiert
Format: JSON
```
**Signale:**
- `ioda_outage_alert_count` — Anzahl aktiver Internet-Ausfall-Alerts pro Land
- `ioda_bgp_visibility_score` — BGP-Sichtbarkeit (0-100%)
**Wert:** Internet-Shutdowns korrelieren stark mit Konflikteeskalation und Repression. Einzige Echtzeit-Quelle dafuer.
**Verifiziert:** `/alerts?entityType=country&limit=5` → Alerts mit Laenderzuordnung ✅

#### OONI Censorship Measurements (Domain E)
```
URL: https://api.ooni.io/api/v1/
Auth: keine
Rate: nicht dokumentiert
Format: JSON
```
**Signale:**
- `ooni_blocked_site_count` — Anzahl blockierter Websites pro Land/Zeitraum
- `ooni_censorship_incident_count` — Gemeldete Zensur-Vorfaelle
**Wert:** Ergaenzt Voidly (Zensur-Score) um tatsaechliche Messungen. Crowdsourced aus 200+ Laendern.
**Verifiziert:** `/aggregation?probe_cc=IR&test_name=web_connectivity` → Daten fuer Iran ✅

#### FEWS NET Food Security (Domain C)
```
URL: https://fdw.fews.net/api/
Auth: keine
Rate: nicht dokumentiert
Format: JSON
Endpoints: marketpricefacts, foodsecurityoutlook, geographicunit, + weitere
```
**Signale:**
- `fewsnet_food_price_index` — Nahrungsmittel-Marktpreise pro Land
- `fewsnet_ipc_phase` — IPC-Ernaehrungssicherheitsphase (1-5)
**Wert:** FEWS NET ist der Gold-Standard fuer Ernaehrungssicherheits-Fruehwarnung. IPC-Phase 3+ = Krise.
**Verifiziert:** `/marketpricefacts/?format=json&country_code=ET` → Aethiopien-Marktpreise ✅

---

## 3. Priorisierte Integrationsreihenfolge

### Phase 1 (P1): Hoechste Wirkung, geringster Aufwand — 6 Adapter

| TAP | API | Domain | Signale | Begruendung |
|-----|-----|--------|---------|-------------|
| AP-15.1 | IMF SDMX | D | CPI, GDP, Commodities | Globale Makro-Luecke schliessen |
| AP-15.2 | WHO GHO (Azure) | C | Life Expectancy, Mortality | Domain C Gesundheitsluecke schliessen |
| AP-15.3 | IDMC Displacement | C | Internal Displacements | Binnenvertreibung als Schluesselindikator |
| AP-15.4 | IODA Outages | E | Internet Ausfaelle | Echtzeit-Repressionsindikator |
| AP-15.5 | OONI Censorship | E | Zensur-Messungen | Ergaenzt Voidly durch echte Messdaten |
| AP-15.6 | FEWS NET | C | Food Prices, IPC Phase | Ernaehrungssicherheits-Fruehwarnung |

### Phase 2 (P2): Wertvolle Ergaenzung — 5 Adapter

| TAP | API | Domain | Signale | Begruendung |
|-----|-----|--------|---------|-------------|
| AP-15.7 | OpenSanctions | B/D | Sanktionierte Entitaeten | Sanktions-Eskalation als Konfliktindikator |
| AP-15.8 | HDX HAPI | B/C | Konflikte, Fluechtlinge, Funding | Umfassende humanitaere Daten |
| AP-15.9 | NASA EONET | C | Naturereignisse | Katastrophen-Fruehwarnung |
| AP-15.10 | BIS Statistics | D | Zentralbank-Raten, Kredit | Monetaere Stabilitaet |
| AP-15.11 | ILO ILOSTAT | D | Arbeitslosigkeit | Arbeitsmarkt als sozialer Stressfaktor |

### Phase 3: Katalog + Registry + Runtime

| TAP | Beschreibung |
|-----|-------------|
| AP-15.12 | Signal-Registry + Feature-Katalog + Quellkatalog Update |
| AP-15.13 | Live-Runtime-Verdrahtung aller neuen Adapter |
| AP-15.14 | Integration-Tests (E2E Pipeline fuer neue Quellen) |

### Phase 4 (P3): Nice-to-have — 5 Adapter (spaeter)

| TAP | API | Domain | Begruendung |
|-----|-----|--------|-------------|
| AP-15.15 | USGS Earthquakes | C | Erdbeben-Echtzeit (Geo-Mapping noetig) |
| AP-15.16 | UN Population | C | Demographische Strukturdaten |
| AP-15.17 | Wikidata SPARQL | A/B | Strukturierte Konflikt-/Putsch-Daten |
| AP-15.18 | RIPE STAT | E | Internet-Infrastruktur-Metriken |
| AP-15.19 | Bluesky API | A | Social-Media-Narrativ-Analyse |

---

## 4. Dependency-Map

```
Phase 1 (P1):
AP-15.1 (IMF) ────────┐
AP-15.2 (WHO) ─────────┤
AP-15.3 (IDMC) ────────┤──→ AP-15.12 (Registry) ──→ AP-15.13 (Runtime) ──→ AP-15.14 (E2E)
AP-15.4 (IODA) ────────┤
AP-15.5 (OONI) ────────┤
AP-15.6 (FEWS NET) ────┘

Phase 2 (P2):
AP-15.7 (OpenSanctions) ──┐
AP-15.8 (HDX HAPI) ───────┤──→ Registry/Runtime Update (inkrementell)
AP-15.9 (NASA EONET) ─────┤
AP-15.10 (BIS) ────────────┤
AP-15.11 (ILO) ────────────┘

Phase 3 (P3): spaeter, unabhaengig
```

## 5. Neue Dependencies (pyproject.toml)
Keine — alle APIs nutzen `urllib`/`json` (bereits vorhanden).

## 6. Erwartete Metriken nach Abschluss Phase 1+2

| Metrik | Aktuell (nach AP-14) | Nach AP-15 Phase 1 | Nach AP-15 Phase 1+2 |
|--------|---------------------|--------------------|-----------------------|
| Adapter total | 16 | 22 | 27 |
| Aktive Signal-Keys | 36 | ~50 | ~65 |
| Software Requirements | 75 | 81 | 86 |
| Domain C Quellen | 3 (UNHCR, HDX-INFORM, GDACS-C) | 6 (+WHO, IDMC, FEWS NET) | 8 (+HDX HAPI, EONET) |
| Domain D Quellen | 5 (WB, Frank, ECB, Eurostat, FX) | 6 (+IMF) | 8 (+BIS, ILO) |
| Domain E Quellen | 4 (CISA, Voidly, NVD, GDELT-E) | 6 (+IODA, OONI) | 6 |

## 7. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| WHO Azure-CDN-Endpoint instabil | niedrig | Retry + Fallback auf Haupt-API falls repariert |
| IMF SDMX-Format komplex | mittel | Bewiesenes Pattern aus ECB-Adapter (AP-14.2) wiederverwenden |
| IODA API-Format aendert sich | niedrig | Schema-Validierung, Version-Pinning |
| FEWS NET nur 30+ Laender | niedrig | Fokus auf Krisenlaender (die sind abgedeckt) |
| OpenSanctions Rate-Limiting | mittel | Caching, moderate Abfrage-Frequenz |
| OONI Datenqualitaet variabel | mittel | Aggregation statt Einzelmessungen |

## 8. Abgrenzung

### In Scope
- Recherche: abgeschlossen (16 APIs verifiziert)
- Phase 1: 6 P1-Adapter mit TDD, V-Model-Chain
- Phase 2: 5 P2-Adapter (wenn Phase 1 abgeschlossen)
- Registry + Runtime-Verdrahtung
- Integration-Tests

### Explizit NICHT in Scope
- P3-APIs (Earthquakes, UN Pop, Wikidata, RIPE, Bluesky) — spaeteres AP
- Kostenpflichtige APIs (bleiben in AP-06)
- ML-Training auf neuen Signalen (separates AP)
- Historische Backfill-Pipelines

---

## 9. V-Model Traceability Vorbereitung
- Pro Adapter: 1 SwR + 1 TC + Trace-Links + Implementation-File-Links
- derives_from: SyR-006 (Datenquellen-Anbindung), SyR-007 (Normalisierung)
- allocated_to: DDS-001
- Signal-Registry muss nach jeder Adapter-Integration aktualisiert werden
- Traceability-Count-Bumps in test_traceability_consistency.py und test_run_artifacts.py
