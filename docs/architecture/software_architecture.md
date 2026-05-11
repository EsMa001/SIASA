# Software Architecture

## Purpose

This document decomposes the SIASA system architecture into software-facing components that can be implemented, verified, and traced to software requirements.

## Architectural decomposition

### DDS-001 Catalog and configuration core
Responsibilities:
- source catalog records
- country-set records
- versioned configuration tables
- domain activation parameters

### DDS-002 Source adapter framework
Responsibilities:
- adapter base interface
- per-source fetch execution
- fetch metadata collection
- failure isolation per source

### DDS-003 Raw and normalized data layer
Responsibilities:
- raw/reference storage
- normalized analytical schemas
- normalization mappings and versions
- provenance persistence

### DDS-004 Feature computation services
Responsibilities:
- shared feature framework
- Domain A, B, D feature services
- selective C/E feature hooks
- coverage/confidence input generation

### DDS-005 Baseline and anomaly services
Responsibilities:
- relative baseline engine
- 30/90/365 combined baseline support
- configurable current windows
- data sufficiency evaluation

### DDS-006 Domain and multi-domain status engines
Responsibilities:
- D0-D5 derivation
- D-status explanation payloads
- S0-S6 derivation
- selective C/E inclusion gate

### DDS-007 Snapshot and traceability core
Responsibilities:
- versioned snapshot schema
- snapshot creation service
- lineage identifiers across all stages

### DDS-008 Reporting and export services
Responsibilities:
- daily global snapshot generator
- country/domain/coverage/event report generators
- export policy enforcement

### DDS-009 Read models and analysis UI services
Responsibilities:
- world anomaly map read model
- country profile read model
- domain detail read models
- source and coverage review read model

### DDS-010 Annotation and validation services
Responsibilities:
- annotation persistence
- annotation non-overwrite policy
- validation case model
- backtest comparison service

### DDS-011 Governance and role enforcement
Responsibilities:
- role model persistence and authorization hooks
- source governance metadata validation
- misuse-boundary guards

### DDS-012 Run orchestration and reprocessing services
Responsibilities:
- daily run orchestrator
- explicit run state model including partial_success
- reprocessing workflow

## Key software interfaces

1. Adapter interface -> normalized record pipeline
2. Normalized record pipeline -> feature services
3. Feature services -> baseline/anomaly services
4. Baseline/anomaly services -> domain status engine
5. Domain status engine -> multi-domain status engine
6. Status engines -> snapshot service
7. Snapshot service -> reporting and read models
8. Annotation and validation services -> read models and reports
9. Governance/role services -> export and operation guards
10. Orchestration service -> all pipeline services

## Traceability expectations

Every implementation module should ultimately trace to:
- one or more SwR IDs
- one DDS allocation target
- one or more TC-SwR verification artifacts

## Next derivation step

The next V-model step after this baseline is implementation slicing and detailed test implementation for the highest-priority software requirements.
