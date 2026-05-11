# System Architecture Overview

This document mirrors the canonical architecture in `vmodel/architecture/system_architecture.md` and is intended for reviewer-friendly reading.

Key points:
- country-centric analytical system
- explicit separation of domains A-E
- rule-based D0-D5 and S0-S6 status logic
- traceability from source to report
- no naive additive overall instability score in the MVP
- governance, ethics, and misuse limits as architectural constraints


# System Architecture

## Purpose

SIASA is a country-centric analytical system for structured assessment of global information and activity spaces under uncertainty. The system is designed to ingest heterogeneous open-source data, preserve traceability across transformation stages, derive explainable domain and multi-domain status values, and support analyst review through a governed UI and reporting layer.

## Architectural principles

1. Country-centric analysis instead of crisis-specific single-use tooling.
2. Explicit domain separation for A-E instead of naive score fusion.
3. Traceability from source catalog to report.
4. Explainable rule-based status logic before complex black-box models.
5. Data sufficiency, coverage, and confidence as first-class artifacts.
6. Governance, ethics, and misuse limits are architectural constraints, not documentation add-ons.

## System context

Inside the system boundary:
- source catalog
- source adapters
- raw data store
- normalization layer
- feature layer
- baseline / anomaly engine
- domain status engine (D0-D5)
- multi-domain status engine (S0-S6)
- snapshot management
- reporting / export layer
- GUI / analysis cockpit
- annotation store
- validation / backtest module
- configuration / rule versioning

Outside the system boundary:
- external data providers
- source uptime and source correctness
- public web platform
- autonomous external agent control

## High-level building blocks

### 1. Source Catalog
Maintains source identity, domain assignment, access mode, history horizon, usage constraints, and governance metadata.

### 2. Source Adapter Layer
Encapsulates retrieval from external sources and isolates source-specific failures, access rules, and schema differences.

### 3. Raw Data Store
Stores permitted raw records or stable references required for reproducibility and later reprocessing.

### 4. Normalization Layer
Transforms heterogeneous source data into country- and time-oriented internal records suitable for downstream analytics.

### 5. Feature Layer
Computes domain-specific analytical features across domains A-E while preserving coverage and explainability context.

### 6. Baseline / Anomaly Engine
Computes relative baselines and anomaly windows using configurable current windows and combined 30/90/365 reference windows.

### 7. Domain Status Engine
Derives D0-D5 per country and domain using rule-based logic, data sufficiency checks, drivers, and uncertainty indicators.

### 8. Multi-Domain Status Engine
Derives S0-S6 from the active domain states while preserving alignment, ambiguity, and insufficiency conditions. No naive additive overall instability score is produced in the MVP baseline.

### 9. Snapshot Management
Persists reproducible run states containing versions, source conditions, derived statuses, and reportable output artifacts.

### 10. Reporting / Export Layer
Produces daily automatic snapshots and manual reports for country, domain, event, and coverage review in governed formats.

### 11. GUI / Analysis Cockpit
Provides the world anomaly map, country profile, domain detail views, source/coverage view, and report/export access.

### 12. Annotation Store
Stores analyst annotations linked to country, domain, signal, event, or snapshot scope without overwriting generated system status.

### 13. Validation / Backtest Module
Maintains reference cases and supports comparison of expected versus observed domain patterns.

### 14. Configuration and Rule Management
Maintains versioned configuration tables, rule sets, and reprocessing readiness.

## Primary data flow

1. Source metadata are selected from the source catalog.
2. Adapters fetch source data or references.
3. Raw records are persisted.
4. Data are normalized into internal country/time-oriented structures.
5. Domain-specific features are computed.
6. Coverage, confidence, and data sufficiency are evaluated.
7. Relative baselines and anomaly measures are computed.
8. Domain statuses D0-D5 are derived.
9. Multi-domain status S0-S6 is derived.
10. A versioned snapshot is persisted.
11. Reports, GUI views, and analyst review artifacts are generated from the snapshot.
12. Traceability links remain available from report back to source metadata.

## Domain model

- Domain A: Information space / narratives / public communication
- Domain B: Event data
- Domain C: Physical activity / satellite / infrastructure
- Domain D: Economic / structural data
- Domain E: Cyber / tech / info-ops

MVP core domains are A, B, and D. Domains C and E are selective and only status-relevant when data quality is sufficient.

## User-facing operating views

- World Anomaly Map
- Global Overview
- Country Profile
- Domain Detail A-E
- Yearly Trend Page
- Current Events Page
- Source / Coverage Page
- Report / Export View
- System Status / Runs
- Backtest / Validation View (prepared/extended)

## Architectural constraints

- No deterministic event prediction.
- No general additive cross-domain crisis score.
- No targeting or operational recommendation functions.
- Public/institutional actor analysis only within governance limits.
- Source dependency, coverage limitations, and uncertainty must remain visible.
- Partial source failure must not silently degrade output quality.

## Mapping from architecture to system responsibilities

| Responsibility | Primary subsystem |
|---|---|
| Source governance | Source Catalog |
| Data ingestion | Source Adapter Layer |
| Reproducibility | Raw Data Store + Snapshot Management |
| Explainability | Feature Layer + Status Engines + Reporting |
| Status generation | Baseline / Anomaly Engine + Status Engines |
| Analyst review | GUI / Analysis Cockpit + Annotation Store |
| Governance and misuse limits | Catalog + Reporting + Role Model + Export Controls |
| Validation | Validation / Backtest Module |

## Next derivation step

The next canonical derivation step is decomposition of these system requirements into software requirements for source adapters, schemas, pipeline orchestration, status logic, reporting, UI services, validation, and governance controls.
