# Software Design Elements

This document mirrors the canonical software design element baseline stored in `vmodel/architecture/software_design_elements.yaml`.

## DDS-001 Catalog and configuration core

Machine-readable catalog, country-set, and configuration services managing source metadata, country priorities, and baseline parameters.

Supports: SyR-004, SyR-005, SyR-006, SyR-030

## DDS-002 Source adapter framework

Reusable adapter abstraction and runtime for heterogeneous external sources with per-source error isolation and fetch metadata.

Supports: SyR-007, SyR-009, SyR-010

## DDS-003 Raw and normalized data layer

Persistent raw/reference storage plus normalized internal schemas for country- and time-oriented processing.

Supports: SyR-008, SyR-011, SyR-018, SyR-019

## DDS-004 Feature computation services

Domain-specific feature builders and shared coverage/confidence inputs.

Supports: SyR-012, SyR-014

## DDS-005 Baseline and anomaly services

Relative baseline, current window, and anomaly computation services.

Supports: SyR-013, SyR-014

## DDS-006 Domain and multi-domain status engines

Rule-based engines for D0-D5 and S0-S6 including selective C/E inclusion and explanation payloads.

Supports: SyR-015, SyR-016, SyR-017

## DDS-007 Snapshot and traceability core

Versioned snapshot persistence and evidence lineage structures from source to report.

Supports: SyR-018, SyR-019

## DDS-008 Reporting and export services

Automated and manual report generation in governed formats with uncertainty and source-state context.

Supports: SyR-025, SyR-027, SyR-028

## DDS-009 Read models and analysis UI services

Query-side read models for world map, country profile, domain detail, source/coverage review, and system status views.

Supports: SyR-020, SyR-021, SyR-022, SyR-023

## DDS-010 Annotation and validation services

Analyst annotations, validation cases, and backtest comparison services.

Supports: SyR-024, SyR-026

## DDS-011 Governance and role enforcement

Role model, export controls, governance constraints, and misuse-boundary enforcement.

Supports: SyR-027, SyR-028, SyR-029

## DDS-012 Run orchestration and reprocessing services

Daily run orchestration, partial-success handling, observability, and controlled reprocessing.

Supports: SyR-009, SyR-010, SyR-030

