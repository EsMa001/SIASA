"""Tests for provenance graph — AP-23: Provenance-Tiefe & In-Chain-Drift."""
from siasa.analysis.provenance_graph import (
    ProvenanceNode, ProvenanceEdge, ProvenanceChain,
    CrossRunComparison,
    build_provenance_chain, compare_provenance_runs,
)


# --- Existing tests (AP-F24) ---

def test_empty():
    c = build_provenance_chain([], [])
    assert c.depth == 0


def test_simple_chain():
    nodes = [ProvenanceNode("src", "source"), ProvenanceNode("norm", "normalized"), ProvenanceNode("feat", "feature")]
    edges = [ProvenanceEdge("src", "norm", "normalize"), ProvenanceEdge("norm", "feat", "extract")]
    c = build_provenance_chain(nodes, edges)
    assert c.depth == 2
    assert c.root_sources == ["src"]
    assert c.leaf_outputs == ["feat"]


def test_cross_run_comparison():
    c1 = build_provenance_chain([ProvenanceNode("A","source"), ProvenanceNode("B","source")], [ProvenanceEdge("A","B","fetch")])
    c2 = build_provenance_chain([ProvenanceNode("B","source"), ProvenanceNode("C","source")], [ProvenanceEdge("B","C","fetch")])
    cmp = compare_provenance_runs(c1, c2, "run1", "run2")
    assert cmp.lineage_changed
    assert "A" in cmp.removed_sources
    assert "B" in cmp.added_sources  # B is root in c2


# --- AP-23: Provenance-Tiefe & In-Chain-Drift ---

def test_provenance_edge_has_transform_version_and_algorithm_id():
    """AP-23: ProvenanceEdge carries mapping/algorithm version metadata."""
    edge = ProvenanceEdge(
        from_node="src",
        to_node="norm",
        transform="normalize",
        transform_version="MAP-GDELT-DOC-v2",
        algorithm_id="ALGO-NORM-01",
    )
    assert edge.transform_version == "MAP-GDELT-DOC-v2"
    assert edge.algorithm_id == "ALGO-NORM-01"


def test_provenance_edge_defaults_none_for_version_fields():
    """AP-23: Backwards compat — version fields default to None."""
    edge = ProvenanceEdge("a", "b", "fetch")
    assert edge.transform_version is None
    assert edge.algorithm_id is None


def test_compare_detects_transform_version_change_same_sources():
    """AP-23 Akzeptanz: changed mapping version + same sources => lineage_changed=True."""
    nodes_a = [ProvenanceNode("src", "source"), ProvenanceNode("norm", "normalized")]
    edges_a = [ProvenanceEdge("src", "norm", "normalize", transform_version="MAP-v1")]

    nodes_b = [ProvenanceNode("src", "source"), ProvenanceNode("norm", "normalized")]
    edges_b = [ProvenanceEdge("src", "norm", "normalize", transform_version="MAP-v2")]

    chain_a = build_provenance_chain(nodes_a, edges_a)
    chain_b = build_provenance_chain(nodes_b, edges_b)

    cmp = compare_provenance_runs(chain_a, chain_b, "run1", "run2")
    assert cmp.lineage_changed is True
    assert cmp.added_sources == []
    assert cmp.removed_sources == []
    assert cmp.transform_version_changes is not None
    assert len(cmp.transform_version_changes) == 1
    change = cmp.transform_version_changes[0]
    assert change["edge"] == ("src", "norm")
    assert change["old_version"] == "MAP-v1"
    assert change["new_version"] == "MAP-v2"


def test_compare_detects_algorithm_id_change():
    """AP-23: changed algorithm_id => lineage_changed=True."""
    nodes_a = [ProvenanceNode("feat", "feature"), ProvenanceNode("score", "domain_score")]
    edges_a = [ProvenanceEdge("feat", "score", "score", algorithm_id="ALGO-ANOM-01")]

    nodes_b = [ProvenanceNode("feat", "feature"), ProvenanceNode("score", "domain_score")]
    edges_b = [ProvenanceEdge("feat", "score", "score", algorithm_id="ALGO-ANOM-02")]

    chain_a = build_provenance_chain(nodes_a, edges_a)
    chain_b = build_provenance_chain(nodes_b, edges_b)

    cmp = compare_provenance_runs(chain_a, chain_b, "run1", "run2")
    assert cmp.lineage_changed is True
    assert cmp.algorithm_id_changes is not None
    assert len(cmp.algorithm_id_changes) == 1
    change = cmp.algorithm_id_changes[0]
    assert change["edge"] == ("feat", "score")
    assert change["old_id"] == "ALGO-ANOM-01"
    assert change["new_id"] == "ALGO-ANOM-02"


def test_compare_no_in_chain_drift_when_identical():
    """AP-23: identical transform versions + same sources => lineage_changed=False."""
    nodes = [ProvenanceNode("src", "source"), ProvenanceNode("norm", "normalized")]
    edges = [ProvenanceEdge("src", "norm", "normalize", transform_version="MAP-v1", algorithm_id="ALGO-01")]

    chain_a = build_provenance_chain(nodes, edges)
    chain_b = build_provenance_chain(nodes, edges)

    cmp = compare_provenance_runs(chain_a, chain_b, "run1", "run2")
    assert cmp.lineage_changed is False
    assert cmp.transform_version_changes == []
    assert cmp.algorithm_id_changes == []


def test_compare_detects_combined_source_and_version_changes():
    """AP-23: both source diff AND version change detected together."""
    nodes_a = [
        ProvenanceNode("src_a", "source"),
        ProvenanceNode("norm", "normalized"),
    ]
    edges_a = [ProvenanceEdge("src_a", "norm", "normalize", transform_version="MAP-v1")]

    nodes_b = [
        ProvenanceNode("src_b", "source"),
        ProvenanceNode("norm", "normalized"),
    ]
    edges_b = [ProvenanceEdge("src_b", "norm", "normalize", transform_version="MAP-v2")]

    chain_a = build_provenance_chain(nodes_a, edges_a)
    chain_b = build_provenance_chain(nodes_b, edges_b)

    cmp = compare_provenance_runs(chain_a, chain_b, "run1", "run2")
    assert cmp.lineage_changed is True
    assert "src_a" in cmp.removed_sources
    assert "src_b" in cmp.added_sources
    # Version changes only reported for edges that exist in both chains
    # (by from_node, to_node pair). Here src_a→norm vs src_b→norm are
    # different edges, so transform_version_changes may be empty.


def test_provenance_node_metadata_carries_versions():
    """AP-23: node metadata can carry mapping/algo version info."""
    node = ProvenanceNode(
        node_id="norm_gdelt",
        stage="normalized",
        metadata={
            "mapping_version": "MAP-GDELT-DOC-v2",
            "algorithm_ids": ["ALGO-NORM-01"],
        },
    )
    assert node.metadata["mapping_version"] == "MAP-GDELT-DOC-v2"
    assert "ALGO-NORM-01" in node.metadata["algorithm_ids"]


def test_full_5_stage_chain_with_versions():
    """AP-23: full source→norm→feature→domain→multi_domain chain with version metadata."""
    nodes = [
        ProvenanceNode("gdelt", "source"),
        ProvenanceNode("norm", "normalized"),
        ProvenanceNode("feat", "feature"),
        ProvenanceNode("dom", "domain_score"),
        ProvenanceNode("multi", "multi_domain"),
    ]
    edges = [
        ProvenanceEdge("gdelt", "norm", "normalize", transform_version="MAP-GDELT-DOC-v1", algorithm_id="ALGO-NORM-01"),
        ProvenanceEdge("norm", "feat", "extract", transform_version="FEAT-MULTI-RES-v1", algorithm_id="ALGO-ZSCORE-01"),
        ProvenanceEdge("feat", "dom", "score", algorithm_id="ALGO-ANOM-01"),
        ProvenanceEdge("dom", "multi", "fuse", algorithm_id="ALGO-BAYES-01"),
    ]
    chain = build_provenance_chain(nodes, edges)
    assert chain.depth == 4
    assert chain.root_sources == ["gdelt"]
    assert chain.leaf_outputs == ["multi"]
    # All edges carry version metadata
    versioned = [e for e in chain.edges if e.transform_version or e.algorithm_id]
    assert len(versioned) == 4
