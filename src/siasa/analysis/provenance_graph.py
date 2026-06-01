"""SIASA provenance graph — full data lineage tracking.

Tracks data from source -> normalization -> feature -> domain -> multi-domain.
Supports cross-run provenance comparison.

Requirement trace: AP-F24, StR-035..039 (Source Lineage)
"""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ProvenanceNode:
    node_id: str
    stage: str  # "source", "normalized", "feature", "domain_score", "multi_domain"
    run_id: str = ""
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class ProvenanceEdge:
    from_node: str
    to_node: str
    transform: str  # "fetch", "normalize", "extract", "score", "fuse"

@dataclass(frozen=True)
class ProvenanceChain:
    nodes: list[ProvenanceNode]
    edges: list[ProvenanceEdge]
    root_sources: list[str]
    leaf_outputs: list[str]
    depth: int

@dataclass(frozen=True)
class CrossRunComparison:
    run_a: str
    run_b: str
    shared_sources: list[str]
    added_sources: list[str]
    removed_sources: list[str]
    lineage_changed: bool

def build_provenance_chain(nodes: list[ProvenanceNode], edges: list[ProvenanceEdge]) -> ProvenanceChain:
    if not nodes:
        return ProvenanceChain([], [], [], [], 0)
    node_ids = {n.node_id for n in nodes}
    targets = {e.to_node for e in edges}
    sources_set = {e.from_node for e in edges}
    roots = sorted(node_ids - targets)
    leaves = sorted(node_ids - sources_set)
    # BFS depth
    adj = {}
    for e in edges:
        adj.setdefault(e.from_node, []).append(e.to_node)
    max_depth = 0
    for root in roots:
        queue = [(root, 0)]
        visited = set()
        while queue:
            cur, d = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            max_depth = max(max_depth, d)
            for nxt in adj.get(cur, []):
                queue.append((nxt, d + 1))
    return ProvenanceChain(nodes=nodes, edges=edges, root_sources=roots, leaf_outputs=leaves, depth=max_depth)

def compare_provenance_runs(chain_a: ProvenanceChain, chain_b: ProvenanceChain, run_a: str, run_b: str) -> CrossRunComparison:
    sources_a = set(chain_a.root_sources)
    sources_b = set(chain_b.root_sources)
    return CrossRunComparison(
        run_a=run_a, run_b=run_b,
        shared_sources=sorted(sources_a & sources_b),
        added_sources=sorted(sources_b - sources_a),
        removed_sources=sorted(sources_a - sources_b),
        lineage_changed=sources_a != sources_b,
    )
