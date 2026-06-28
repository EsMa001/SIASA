"""SIASA provenance graph — full data lineage tracking.

Tracks data from source -> normalization -> feature -> domain -> multi-domain.
Supports cross-run provenance comparison with in-chain drift detection.

Requirement trace: AP-F24 (StR-035..039), AP-23 (F6: Provenance-Tiefe & In-Chain-Drift)
Algorithm: ALGO-PROV-02 (in-chain transform/version diff)
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProvenanceNode:
    """A node in the provenance chain (one processing stage)."""
    node_id: str
    stage: str  # "source", "normalized", "feature", "domain_score", "multi_domain"
    run_id: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProvenanceEdge:
    """An edge linking two provenance nodes via a transform.

    AP-23 extension: carries transform_version and algorithm_id so that
    in-chain drift (same source graph, changed processing) is detectable.
    """
    from_node: str
    to_node: str
    transform: str  # "fetch", "normalize", "extract", "score", "fuse"
    transform_version: str | None = None  # e.g. "MAP-GDELT-DOC-v2"
    algorithm_id: str | None = None  # e.g. "ALGO-ANOM-01"


@dataclass(frozen=True)
class ProvenanceChain:
    """Complete provenance chain with root/leaf detection and BFS depth."""
    nodes: list[ProvenanceNode]
    edges: list[ProvenanceEdge]
    root_sources: list[str]
    leaf_outputs: list[str]
    depth: int


@dataclass(frozen=True)
class CrossRunComparison:
    """Result of comparing two provenance chains across runs.

    AP-23 extension: transform_version_changes and algorithm_id_changes
    detect in-chain drift even when source graphs are identical.
    """
    run_a: str
    run_b: str
    shared_sources: list[str]
    added_sources: list[str]
    removed_sources: list[str]
    lineage_changed: bool
    transform_version_changes: list[dict] = field(default_factory=list)
    algorithm_id_changes: list[dict] = field(default_factory=list)


def build_provenance_chain(nodes: list[ProvenanceNode], edges: list[ProvenanceEdge]) -> ProvenanceChain:
    """Build a provenance chain from nodes and edges, computing root/leaf/depth."""
    if not nodes:
        return ProvenanceChain([], [], [], [], 0)
    node_ids = {n.node_id for n in nodes}
    targets = {e.to_node for e in edges}
    sources_set = {e.from_node for e in edges}
    roots = sorted(node_ids - targets)
    leaves = sorted(node_ids - sources_set)
    # BFS depth
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e.from_node, []).append(e.to_node)
    max_depth = 0
    for root in roots:
        queue = [(root, 0)]
        visited: set[str] = set()
        while queue:
            cur, d = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            max_depth = max(max_depth, d)
            for nxt in adj.get(cur, []):
                queue.append((nxt, d + 1))
    return ProvenanceChain(nodes=nodes, edges=edges, root_sources=roots, leaf_outputs=leaves, depth=max_depth)


def compare_provenance_runs(
    chain_a: ProvenanceChain,
    chain_b: ProvenanceChain,
    run_a: str,
    run_b: str,
) -> CrossRunComparison:
    """Compare two provenance chains, detecting source and in-chain drift.

    AP-23 / ALGO-PROV-02: beyond root-source diff, detects:
    - transform_version changes on matching edges
    - algorithm_id changes on matching edges
    Either kind of change sets lineage_changed=True.
    """
    sources_a = set(chain_a.root_sources)
    sources_b = set(chain_b.root_sources)

    # Build edge index keyed by (from_node, to_node) for in-chain comparison
    edges_a_by_key = {(e.from_node, e.to_node): e for e in chain_a.edges}
    edges_b_by_key = {(e.from_node, e.to_node): e for e in chain_b.edges}

    shared_edge_keys = set(edges_a_by_key.keys()) & set(edges_b_by_key.keys())

    transform_version_changes: list[dict] = []
    algorithm_id_changes: list[dict] = []

    for key in sorted(shared_edge_keys):
        ea = edges_a_by_key[key]
        eb = edges_b_by_key[key]

        if ea.transform_version != eb.transform_version and (
            ea.transform_version is not None or eb.transform_version is not None
        ):
            transform_version_changes.append({
                "edge": key,
                "old_version": ea.transform_version,
                "new_version": eb.transform_version,
            })

        if ea.algorithm_id != eb.algorithm_id and (
            ea.algorithm_id is not None or eb.algorithm_id is not None
        ):
            algorithm_id_changes.append({
                "edge": key,
                "old_id": ea.algorithm_id,
                "new_id": eb.algorithm_id,
            })

    source_changed = sources_a != sources_b
    in_chain_changed = bool(transform_version_changes) or bool(algorithm_id_changes)

    return CrossRunComparison(
        run_a=run_a,
        run_b=run_b,
        shared_sources=sorted(sources_a & sources_b),
        added_sources=sorted(sources_b - sources_a),
        removed_sources=sorted(sources_a - sources_b),
        lineage_changed=source_changed or in_chain_changed,
        transform_version_changes=transform_version_changes,
        algorithm_id_changes=algorithm_id_changes,
    )
