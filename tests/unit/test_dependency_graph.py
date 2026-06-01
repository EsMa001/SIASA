"""Tests for dependency graph and cluster detection."""
from siasa.analysis.dependency_graph import DependencyEdge, build_dependency_graph

def test_empty_graph():
    result = build_dependency_graph([])
    assert result.source_count == 0

def test_simple_graph():
    edges = [DependencyEdge("A", "B", 0.8, 2.0), DependencyEdge("B", "C", 0.6, 4.0)]
    result = build_dependency_graph(edges)
    assert result.source_count == 3
    assert len(result.clusters) == 1

def test_disconnected_components():
    edges = [DependencyEdge("A", "B", 0.8), DependencyEdge("C", "D", 0.6)]
    result = build_dependency_graph(edges)
    assert len(result.clusters) == 2

def test_influence_scores():
    edges = [DependencyEdge("A", "B", 0.8), DependencyEdge("A", "C", 0.7)]
    result = build_dependency_graph(edges)
    a = next(s for s in result.influence_scores if s.source_id == "A")
    assert a.out_degree == 2

def test_cluster_cohesion():
    edges = [DependencyEdge("A", "B", 0.9), DependencyEdge("B", "A", 0.8)]
    result = build_dependency_graph(edges)
    assert result.clusters[0].cohesion == 0.85
