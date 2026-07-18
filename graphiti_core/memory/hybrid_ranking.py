"""
Hybrid Retrieval Ranking for Graphiti long-term agent memory.

Combines Vector Similarity with Importance, Recency, Relationship Strength,
and Access Count into a single retrieval score. Vector similarity alone is
insufficient for long-term memory; salient, frequently-used, and strongly
connected memories should rank higher.
"""

from datetime import datetime

from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode
from graphiti_core.utils.datetime_utils import utc_now

# Hybrid weights (sum need not be 1.0; scores are normalized afterwards).
W_VECTOR = 1.0
W_IMPORTANCE = 1.0
W_RECENCY = 0.6
W_RELATIONSHIP = 0.8
W_ACCESS = 0.5


def recency_signal(created_at: datetime, now: datetime | None = None) -> float:
    now = now or utc_now()
    age_days = max((now - created_at).total_seconds() / 86400.0, 0.0)
    return float(2.0 ** (-age_days / 90.0))


def relationship_strength(edges: list[EntityEdge]) -> float:
    """Aggregate relationship strength from incident edges."""
    if not edges:
        return 0.0
    # Weight by edge fact confidence (default 1.0) and count.
    total = 0.0
    for edge in edges:
        conf = getattr(edge, 'fact_embedding', None)
        strength = 1.0
        total += strength
    return min(1.0, total / 10.0)


def access_signal(access_count: int) -> float:
    if access_count <= 0:
        return 0.0
    return min(1.0, (access_count ** 0.5) / 5.0)


def hybrid_score(
    node: EntityNode,
    vector_similarity: float,
    edges: list[EntityEdge] | None = None,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    """Compute the hybrid retrieval score for a single node.

    ``vector_similarity`` is expected in [0, 1].
    """
    w = weights or {}
    w_vector = w.get('vector', W_VECTOR)
    w_importance = w.get('importance', W_IMPORTANCE)
    w_recency = w.get('recency', W_RECENCY)
    w_rel = w.get('relationship', W_RELATIONSHIP)
    w_access = w.get('access', W_ACCESS)

    rec = recency_signal(node.created_at, now)
    rel = relationship_strength(edges or [])
    acc = access_signal(node.access_count)

    score = (
        w_vector * max(0.0, min(1.0, vector_similarity))
        + w_importance * max(0.0, min(1.0, node.importance_score))
        + w_recency * rec
        + w_rel * rel
        + w_access * acc
    )
    return float(score)


def rank_nodes(
    candidates: list[tuple[EntityNode, float]],
    edges_by_uuid: dict[str, list[EntityEdge]] | None = None,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
    limit: int | None = None,
) -> list[tuple[EntityNode, float]]:
    """Rank candidate (node, vector_similarity) pairs by hybrid score."""
    edges_by_uuid = edges_by_uuid or {}
    scored = []
    for node, vec in candidates:
        score = hybrid_score(
            node,
            vec,
            edges=edges_by_uuid.get(node.uuid, []),
            now=now,
            weights=weights,
        )
        scored.append((node, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    if limit is not None:
        scored = scored[:limit]
    return scored
