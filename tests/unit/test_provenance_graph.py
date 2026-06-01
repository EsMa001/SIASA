"""Tests for provenance graph."""
from siasa.analysis.provenance_graph import ProvenanceNode, ProvenanceEdge, build_provenance_chain, compare_provenance_runs

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
