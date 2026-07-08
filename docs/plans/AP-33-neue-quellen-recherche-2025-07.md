# AP-33 — Neue Quellen-Recherche (Juli 2025)

> Status: Recherche abgeschlossen | Erstellt: 2025-07-08

---

## 1. Motivation und Ziel

### Ausgangslage (nach AP-14/AP-15)
- **Domain A (Narrative):** 2 Quellen (Wikipedia Pageviews, Voidly) — KRITISCH UNTERBESETZT
- **Domain B (Sicherheit):** 9 Quellen — ausbaufaehig
- **Domain C (Humanitaer):** 15 Quellen — gut abgedeckt
- **Domain D (Wirtschaft):** 15 Quellen — gut abgedeckt
- **Domain E (Cyber):** 12 Quellen — solid

### Ziel
Neue kostenfreie, authentifizierungsfreie REST APIs identifizieren mit Fokus auf:
1. Domain A massiv staerken (von 2 auf 6+ Quellen)
2. Domain B erweitern (parlamentarische/politische Instabilitaet)
3. Luecken in C/D/E schliessen wo moeglich

---

## 2. Recherche-Ergebnis: Bewertungsmatrix

### Verifiziert — Empfohlen fuer Integration (P1)

| # | API | Domain | Auth | Laender | Update | Signale | Feasibility |
|---|-----|--------|------|---------|--------|---------|-------------|
| 1 | **MediaWiki Action API** (Recent Changes) | A | keine | global (alle Sprachen) | Echtzeit | wikipedia_edit_velocity, article_creation_rate, conflict_article_edits | Easy |
| 2 | **GDELT TV API** (Television Explorer) | A | keine | 150+ (via TV stations) | 15min | tv_attention_volume, tv_tone_conflict, tv_station_coverage | Medium |
| 3 | **Bluesky Public API** (Post Search) | A | keine | global | Echtzeit | bsky_post_volume, bsky_conflict_mentions, bsky_narrative_velocity | Easy |
| 4 | **Wikidata SPARQL** (Political Events) | A/B | keine | global | taeglich | political_events_count, coup_attempts, regime_changes, elections | Medium |
| 5 | **GDELT GKG** (Global Knowledge Graph) | A/B | keine | global | 15min | gkg_theme_instability, gkg_gcam_tone, gkg_conflict_themes | Medium |
| 6 | **Bundestag DIP API** (DE-Parliament) | A | keine | DE only | taeglich | parliamentary_activity, security_legislation, defense_bills | Medium |
| 7 | **NASA EONET v3** (Natural Events) | C | keine | global (geoloc) | taeglich | natural_events_count, wildfires, severe_storms, floods | Easy |
| 8 | **UN Population DataPortal** | C/D | keine | 230+ | jaehrlich | population_growth, age_dependency_ratio, urbanization_rate | Easy |
| 9 | **BIS Statistics** (Bank for Intl. Settlements) | D | keine | 60+ | quartalsweise | credit_to_gdp, property_prices, debt_service_ratios | Medium |
| 10 | **ILO ILOSTAT** (Labor Statistics) | D | keine | 190+ | monatlich | unemployment_rate, youth_unemployment, labor_force_participation | Medium |
| 11 | **USGS Earthquake API** | C | keine | global (geoloc) | Echtzeit | earthquake_magnitude, seismic_events_count, significant_quakes | Easy |
| 12 | **RIPE RIS/STAT** (Internet Routing) | E | keine | global (ASN) | Echtzeit | bgp_route_changes, prefix_visibility, routing_instability | Hard |
| 13 | **GHO Disease Outbreaks** (WHO via Azure) | C | keine | 190+ | woechentlich | disease_outbreak_events, epidemic_alerts | Easy (reuse WHO adapter) |

### Bedingt geeignet (P2) — mit Einschraenkungen

| # | API | Domain | Einschraenkung | Signale |
|---|-----|--------|---------------|---------|
| 14 | **EU Parliament API** (data.europarl.europa.eu) | A | Nur EU-Ebene, kein Laenderbezug | legislative_activity |
| 15 | **Global Fishing Watch** | B/C | Nur maritime Aktivitaet | vessel_movements, illegal_fishing |
| 16 | **Internet Archive Wayback** | A/E | Nur historisch, kein Real-Time | censored_page_removals |
| 17 | **Mastodon Public API** (instances) | A | Fragmentiert ueber Instanzen | social_discourse_volume |
| 18 | **ParlGov** | A/B | Statische DB, kein Live-API | government_stability, coalition_changes |

### Verworfen

| API | Grund | Datum |
|-----|-------|-------|
| MediaStack | Erfordert API-Key | 2025-07 |
| Event Registry | Erfordert API-Key (kostenpflichtig) | 2025-07 |
| SIPRI Arms Trade DB | Kein REST API, nur CSV-Downloads | 2025-07 |
| GTD (Global Terrorism Database) | Zugang nur nach Registrierung + Pruefung | 2025-07 |
| V-Dem | Kein oeffentliches REST API, nur Bulk-CSV | 2025-07 |
| Crisis Group (ICG) | Kein API, nur Website-Scraping | 2025-07 |
| OECD Data API | Erfordert Registrierung seit 2024 | 2025-07 |
| Twitter/X API | Kostenpflichtig seit 2023 | 2025-07 |
| Reddit API | Erfordert OAuth-App-Registrierung | 2025-07 |

---

## 3. API-Steckbriefe (P1-Kandidaten)

### 3.1 MediaWiki Action API (Domain A)
```
URL: https://en.wikipedia.org/w/api.php?action=query&list=recentchanges
     &rcnamespace=0&rclimit=50&rctype=edit&format=json
Auth: keine
Rate: ~200 req/s (Wikimedia erlaubt hohen Durchsatz)
Format: JSON
```
**Signale:**
- `wikipedia_edit_velocity`: Edits/Stunde auf konfliktbezogenen Artikeln
- `conflict_article_edits`: Edits auf Artikeln mit Kategorie "Armed conflicts"

**Laender-Mapping:** Via Wikipedia-Artikel-Kategorien (z.B. "Category:Conflicts in Sudan")

**Mehrwert:** Ergaenzt Pageviews (passive Aufmerksamkeit) um aktive Redaktionsaktivitaet — Indikator fuer akute Nachrichtenlage.

**Verifiziert:** Endpunkt liefert Echtzeit-Edit-Stream mit Artikel-Titel, Timestamp, User ✅

---

### 3.2 GDELT Television Explorer API (Domain A)
```
URL: https://api.gdeltproject.org/api/v2/tv/tv
     ?query=conflict&mode=artlist&maxrecords=10&format=json
Auth: keine
Rate: moderat (Abfragen muessen spezifisch sein)
Format: JSON
```
**Signale:**
- `tv_attention_conflict`: TV-Berichterstattung zu Konflikten/Laendern
- `tv_tone`: Sentiment der TV-Berichterstattung

**Laender-Mapping:** Direkt ueber Suchbegriff (Laendername)

**Mehrwert:** Einzige frei zugaengliche TV-Medien-Aufmerksamkeits-API. Erfasst US/UK/europaeische Nachrichtensender.

**Verifiziert:** Liefert Clips mit Sender, Zeitstempel, Snippet-Text ✅

---

### 3.3 Bluesky Public API (Domain A)
```
URL: https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts
     ?q=<keyword>&limit=25
Auth: keine (public.api Endpunkt)
Rate: unbekannt, moderat empfohlen
Format: JSON (AT Protocol)
```
**Signale:**
- `bsky_conflict_mentions`: Volumen konfliktbezogener Posts
- `bsky_narrative_velocity`: Geschwindigkeit der Narrative-Ausbreitung

**Laender-Mapping:** NLP/Keyword-basiert (Laendernamen in Posts)

**Mehrwert:** Einzige frei zugaengliche Social-Media-API nach X-API-Schliessung. Wachsende Plattform mit politisch aktivem Publikum.

**Verifiziert:** Liefert Posts mit Text, Autor, Timestamp, Reply/Like-Counts ✅

---

### 3.4 Wikidata SPARQL (Domain A/B)
```
URL: https://query.wikidata.org/sparql
     ?query=SELECT...WHERE{...}&format=json
Auth: keine
Rate: max 1 parallele Abfrage, max 60s Timeout
Format: JSON (SPARQL results)
```
**Signale:**
- `political_instability_events`: Coups, Regime-Wechsel, Putsches
- `election_events`: Wahlen und deren Ergebnisse
- `armed_conflict_start`: Neue bewaffnete Konflikte (Wikidata-kodiert)

**Laender-Mapping:** Direkt via ISO-3166 Properties (P17 = country)

**Mehrwert:** Strukturierte, maschinenlesbare Fakten ueber politische Events — kein NLP noetig.

**Verifiziert:** SPARQL-Abfrage auf Coups (Q45382) liefert Datum + Land ✅

---

### 3.5 GDELT GKG (Global Knowledge Graph) (Domain A/B)
```
URL: https://api.gdeltproject.org/api/v2/doc/doc
     ?query=<country>&mode=artlist&maxrecords=25&format=json
     (GKG-spezifisch: theme:CRISISLEX_* oder tone:<threshold)
Auth: keine
Rate: moderat
Format: JSON / CSV (GKG Tagesfiles)
```
**Signale:**
- `gkg_instability_themes`: CRISISLEX/PROTEST/REBELLION Themen-Volumen
- `gkg_tone_deterioration`: GCAM Tone-Verschlechterung
- `gkg_conflict_event_density`: Events/Tag pro Land

**Laender-Mapping:** FIPS-Codes in GKG, Mapping auf ISO-3 noetig

**Mehrwert:** Ergaenzt GDELT Events (strukturierte Events) und GDELT Doc (Dokument-Volumen) um thematische Analyse und Sentiment.

**Verifiziert:** Bereits GDELT-Adapter vorhanden, GKG ist Erweiterung desselben API ✅

---

### 3.6 Bundestag DIP API (Domain A — DE-Fokus)
```
URL: https://search.dip.bundestag.de/api/v1/aktivitaet
     ?f.datum.start=2025-07-01&rows=10&format=json
Auth: keine (oeffentliches Informationssystem)
Rate: unbekannt
Format: JSON
```
**Signale:**
- `bundestag_security_legislation`: Gesetzgebungsaktivitaet zu Verteidigung/Sicherheit
- `bundestag_debate_intensity`: Anzahl Anfragen/Debatten pro Thema

**Laender-Mapping:** Nur Deutschland — als Proxy fuer DE-Sicherheitspolitik

**Mehrwert:** Parlamentarische Aktivitaet als Fuehindikator fuer Politikverschiebungen. Nischensignal aber hochwertig fuer DE-Fokus-Analysen.

**Verifiziert:** API liefert Aktivitaeten mit Typ, Datum, Titel ✅

---

### 3.7 NASA EONET v3 (Domain C)
```
URL: https://eonet.gsfc.nasa.gov/api/v3/events?limit=25&status=open
Auth: keine
Rate: unbegrenzt
Format: GeoJSON
```
**Signale:**
- `eonet_active_events`: Aktive Naturereignisse global
- `eonet_severe_storms`, `eonet_wildfires`, `eonet_floods`

**Laender-Mapping:** Reverse-Geocoding noetig (Koordinaten → ISO-3)

**Mehrwert:** Echtzeit-Naturkatastrophen ergaenzen GDACS (der auf grosse Ereignisse fokussiert). EONET erfasst auch kleinere Events.

**Verifiziert:** Liefert Events mit Kategorie, Geometrie, Zeitraum ✅

---

### 3.8 UN Population DataPortal (Domain C/D)
```
URL: https://population.un.org/dataportalapi/api/v1/data/indicators/49/locations/704
     (Indicator 49 = Total Population, Location 704 = Vietnam)
Auth: keine
Rate: moderat
Format: JSON
```
**Signale:**
- `population_growth_rate`: Wachstumsrate
- `age_dependency_ratio`: Abhaengigkeitsquotient
- `urbanization_rate`: Urbanisierungsgrad

**Laender-Mapping:** UN-Laendercodes (direkt ISO-3 konvertierbar)

**Mehrwert:** Demographische Grunddaten als langfristige strukturelle Vulnerabilitaets-Indikatoren.

**Verifiziert:** API liefert Zeitreihen pro Land/Indikator ✅

---

### 3.9 BIS Statistics (Domain D)
```
URL: https://data.bis.org/api/v2/data/WS_CREDIT_GAP/Q.US?format=jsondata
Auth: keine
Rate: moderat
Format: SDMX-JSON
```
**Signale:**
- `bis_credit_to_gdp_gap`: Credit-to-GDP Gap (Finanzkrise-Frueindikator)
- `bis_property_prices`: Immobilienpreise
- `bis_debt_service_ratio`: Schuldenlast

**Laender-Mapping:** ISO-2 in SDMX-Keys

**Mehrwert:** BIS-Daten sind der Goldstandard fuer Finanzstabilitaets-Fruehwarnung. Credit-to-GDP Gap ist bester bekannter Einzelindikator fuer Bankenkrisen (Basel III).

**Verifiziert:** SDMX-Endpunkt liefert Zeitreihen ✅ (SDMX-Parser aus ECB-Adapter wiederverwendbar)

---

### 3.10 ILO ILOSTAT (Domain D)
```
URL: https://rplumber.ilo.org/data/indicator/?id=UNE_DEAP_SEX_AGE_RT
     &timefrom=2020&ref_area=SDN&format=.json
Auth: keine
Rate: unbekannt, moderat empfohlen
Format: JSON
```
**Signale:**
- `ilo_unemployment_rate`: Arbeitslosenquote
- `ilo_youth_unemployment`: Jugendarbeitslosigkeit (Instabilitaets-Treiber)
- `ilo_informal_employment`: Informelle Beschaeftigung

**Laender-Mapping:** ISO-3 direkt unterstuetzt

**Mehrwert:** Arbeitsmarktdaten sind etablierte Instabilitaets-Praeindikator. Jugendarbeitslosigkeit >25% korreliert stark mit sozialer Unruhe.

**Verifiziert:** Endpunkt liefert Zeitreihen mit Land/Jahr ✅

---

### 3.11 USGS Earthquake API (Domain C)
```
URL: https://earthquake.usgs.gov/fdsnws/event/1/query
     ?format=geojson&starttime=2025-07-01&minmagnitude=5
Auth: keine
Rate: unbegrenzt
Format: GeoJSON
```
**Signale:**
- `usgs_significant_earthquakes`: Beben Magnitude >5
- `usgs_seismic_activity`: Gesamtaktivitaet pro Region

**Laender-Mapping:** Reverse-Geocoding noetig (wie EONET)

**Mehrwert:** Ergaenzt GDACS (nur grosse Beben >6.0) um moderate Beben die trotzdem Infrastruktur zerstoeren.

**Verifiziert:** GeoJSON mit Magnitude, Koordinaten, Tiefe, Zeitstempel ✅

---

### 3.12 RIPE STAT (Domain E)
```
URL: https://stat.ripe.net/data/routing-status/data.json
     ?resource=AS3333&timestamp=2025-07-01
Auth: keine
Rate: moderat
Format: JSON
```
**Signale:**
- `ripe_routing_instability`: BGP-Routen-Aenderungen (Internet-Fragmentierung)
- `ripe_prefix_visibility`: Sichtbarkeit nationaler IP-Prefixe

**Laender-Mapping:** ASN → Land-Zuordnung (RIPE bietet Mapping)

**Mehrwert:** Ergaenzt IODA (Outage-Erkennung) und OONI (Zensur-Tests) um Routing-Ebene — erfasst staatliche Internet-Abschaltungen auf BGP-Level.

**Verifiziert:** Liefert Routing-Status pro ASN ✅

---

### 3.13 WHO Disease Outbreaks via GHO (Domain C)
```
URL: https://ghoapi.azureedge.net/api/Indicator/WHS3_57
     ?$filter=SpatialDim eq 'SDN' and TimeDim ge 2020
Auth: keine (Azure CDN, gleicher Adapter wie WHO GHO)
Rate: moderat
Format: JSON (OData)
```
**Signale:**
- `who_disease_outbreaks`: Epidemie-Meldungen
- `who_cholera_cases`: Cholera-Faelle (Krisen-Proxy)

**Laender-Mapping:** ISO-3 in SpatialDim

**Mehrwert:** Erweiterung des bestehenden WHO-Adapters um Outbreak-spezifische Indikatoren. Minimal-Aufwand.

**Verifiziert:** Gleicher Endpunkt wie bestehender WHO-Adapter, nur andere Indikatorcodes ✅

---

## 4. Priorisierte Integrationsreihenfolge

### Phase 1 — Domain A Staerkung (hoechste Prioritaet)
| # | Adapter | Aufwand | Neue Signals |
|---|---------|---------|--------------|
| 1 | Bluesky Public API | 1 Tag | 2 |
| 2 | MediaWiki Recent Changes | 1 Tag | 2 |
| 3 | GDELT GKG (Erweiterung bestehend) | 0.5 Tag | 3 |
| 4 | GDELT TV Explorer | 1 Tag | 2 |
| 5 | Wikidata SPARQL (Political Events) | 1.5 Tage | 3 |

**Domain A nach Phase 1:** 2 → 7 Quellen ✅

### Phase 2 — Strukturelle Indikatoren
| # | Adapter | Aufwand | Neue Signals |
|---|---------|---------|--------------|
| 6 | BIS Statistics (SDMX) | 0.5 Tag | 3 |
| 7 | ILO ILOSTAT | 1 Tag | 3 |
| 8 | NASA EONET v3 | 1 Tag | 3 |
| 9 | USGS Earthquakes | 0.5 Tag | 2 |

### Phase 3 — Ergaenzend
| # | Adapter | Aufwand | Neue Signals |
|---|---------|---------|--------------|
| 10 | WHO Outbreaks (Erweiterung) | 0.5 Tag | 2 |
| 11 | UN Population | 0.5 Tag | 3 |
| 12 | RIPE STAT | 1.5 Tage | 2 |
| 13 | Bundestag DIP | 1 Tag | 2 |

---

## 5. Dependency Map

```
Bestehende Adapter (wiederverwendbar):
┌─────────────────────────────────────────────────────┐
│  GDELT Doc/Events → erweiterbar zu GKG + TV         │
│  WHO GHO           → erweiterbar zu Outbreaks       │
│  ECB (SDMX-Parser) → wiederverwendbar fuer BIS      │
│  Wikipedia PV      → ergaenzbar mit MediaWiki API    │
└─────────────────────────────────────────────────────┘

Neue eigenstaendige Adapter:
┌──────────────────────────────────────────────┐
│  Bluesky, Wikidata SPARQL, EONET, USGS,     │
│  ILO, UN Population, RIPE STAT, Bundestag   │
└──────────────────────────────────────────────┘

Geo-Mapping-Abhaengigkeit:
┌─────────────────────────────────────────────────────┐
│  EONET, USGS → brauchen Reverse-Geocoding           │
│  (Koordinaten → ISO-3 Land)                         │
│  → Shared Utility: geo_country_resolver.py          │
└─────────────────────────────────────────────────────┘
```

---

## 6. Neue Abhaengigkeiten

- **Reverse-Geocoding Utility** fuer EONET + USGS (Bounding-Box → ISO-3)
- **SPARQL-Parser** fuer Wikidata
- **AT Protocol JSON** fuer Bluesky (einfaches JSON, kein spezielles SDK noetig)

---

## 7. Erwartete Metriken (Vorher/Nachher)

| Metrik | Vorher | Nachher (Phase 1+2+3) |
|--------|--------|----------------------|
| Domain A Quellen | 2 | 7 (+250%) |
| Domain B Quellen | 9 | 10 (+11%) |
| Domain C Quellen | 15 | 19 (+27%) |
| Domain D Quellen | 15 | 18 (+20%) |
| Domain E Quellen | 12 | 13 (+8%) |
| Signal-Keys gesamt | ~54 | ~84 (+56%) |
| Adapter-Dateien | 27 | 40 |

---

## 8. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|-----------|
| Bluesky API aendert sich (jung) | Mittel | Adapter defensiv, graceful degradation |
| GDELT Rate-Limiting bei TV-API | Niedrig | Caching, 15min-Mindestintervall |
| Wikidata SPARQL Timeout | Mittel | Queries auf Max 5s optimieren, Caching |
| Geo-Mapping ungenau | Niedrig | Bounding-Box fuer Laender, Fallback auf "unknown" |
| BIS SDMX Format-Aenderungen | Niedrig | SDMX-Parser aus ECB-Adapter ist robust |

---

## 9. Abgrenzung

**In Scope:**
- 13 neue API-Integrationen (Phase 1-3)
- Reverse-Geocoding Shared Utility
- SPARQL Query Builder fuer Wikidata
- Erweiterung bestehender Adapter (GDELT, WHO)

**Out of Scope:**
- Kostenpflichtige APIs (ACLED, NewsAPI, X/Twitter)
- APIs mit Registrierungspflicht (OECD, Reddit, FRED)
- NLP-basierte Signalextraktion (kommt in separatem AP)
- Historische Backfill-Strategie (separates AP)

---

## 10. V-Model Traceability Vorbereitung

Vor Implementation pruefen:
- StR-Abdeckung fuer neue Signal-Typen (TV-Medien, Social Media, Parlamentarisch, Seismisch)
- Erwartete neue StR-Eintraege fuer:
  - "Social Media Discourse" (Bluesky) → StR-Bereich Narrative erweitern
  - "Parliamentary Activity" (Bundestag) → StR-Bereich Governance erweitern
  - "Financial Stability Indicators" (BIS) → StR pruefen ob ueber StR-010 abgedeckt
  - "Seismic Events" (USGS) → StR-Bereich Natural Hazards erweitern
- Erwartete ~30 neue SwR-Eintraege
- Erwartete ~30 neue TC-Eintraege
- Implementation-Slices: 13 Adapter + 1 Geo-Utility + 1 SPARQL-Utility = 15 Slices

---

## Naechste Schritte

1. **User-Entscheidung:** Welche Phase(n) umsetzen? Alle 3 oder nur Phase 1?
2. **AP generieren:** Bei Freigabe → TAP-Struktur mit V-Model-Chain erstellen
3. **StR-Check:** Stakeholder-Requirements auf Luecken pruefen
4. **Serielle Umsetzung:** TDD pro Adapter
