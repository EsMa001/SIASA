"""SIASA source dependency graph and cluster detection.

Models source-to-source dependencies as a directed graph, detects
clusters of tightly coupled sources, and quantifies influence.

Requirement trace: AP-F23, StR-029..034 (Informationsabhängigkeiten)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict


@dataclass(frozen=True)
class DependencyEdge:
    """A directed dependency between two sources."""
    source_from: str
    source_to: str
    weight: float
    timing_lag_hours: float = 0.0


@dataclass(frozen=True)
class DependencyCluster:
    """A cluster of tightly coupled sources."""
    cluster_id: str
    sources: list[str]
    internal_edge_count: int
    cohesion: float


@dataclass(frozen=True)
class InfluenceScore:
    """Influence quantification for a source."""
    source_id: str
    in_degree: int
    out_degree: int
    influence_score: float


@dataclass(frozen=True)
class DependencyGraphResult:
    """Full dependency graph analysis result."""
    edges: list[DependencyEdge]
    clusters: list[DependencyCluster]
    influence_scores: list[InfluenceScore]
    source_count: int
    edge_count: int


def build_dependency_graph(edges: list[DependencyEdge]) -> DependencyGraphResult:
    """Build dependency graph, detect clusters, compute influence."""
    if not edges:
        return DependencyGraphResult([], [], [], 0, 0)

    sources: set[str] = set()
    adj: dict[str, set[str]] = defaultdict(set)
    in_deg: dict[str, int] = defaultdict(int)
    out_deg: dict[str, int] = defaultdict(int)

    for edge in edges:
        sources.add(edge.source_from)
        sources.add(edge.source_to)
        adj[edge.source_from].add(edge.source_to)
        adj[edge.source_to].add(edge.source_from)
        out_deg[edge.source_from] += 1
        in_deg[edge.source_to] += 1

    visited: set[str] = set()
    clusters: list[DependencyCluster] = []
    cluster_idx = 0

    for source in sorted(sources):
        if source in visited:
            continue
        component: list[str] = []
        stack = [source]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in sorted(adj[node]):
                if neighbor not in visited:
                    stack.append(neighbor)

        if len(component) >= 2:
            comp_set = set(component)
            internal_edges = sum(
                1 for e in edges
                if e.source_from in comp_set and e.source_to in comp_set
            )
            avg_weight = (
                sum(e.weight for e in edges if e.source_from in comp_set and e.source_to in comp_set)
                / max(internal_edges, 1)
            )
            clusters.append(DependencyCluster(
                cluster_id=f"CLUSTER-{cluster_idx:03d}",
                sources=sorted(component),
                internal_edge_count=internal_edges,
                cohesion=round(avg_weight, 4),
            ))
            cluster_idx += 1

    total_sources = len(sources)
    influence_scores = [
        InfluenceScore(
            source_id=s,
            in_degree=in_deg.get(s, 0),
            out_degree=out_deg.get(s, 0),
            influence_score=round(out_deg.get(s, 0) / max(total_sources, 1), 4),
        )
        for s in sorted(sources)
    ]

    return DependencyGraphResult(
        edges=edges,
        clusters=clusters,
        influence_scores=influence_scores,
        source_count=len(sources),
        edge_count=len(edges),
    )
