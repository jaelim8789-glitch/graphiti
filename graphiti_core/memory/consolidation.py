"""
Memory Consolidation for Graphiti long-term agent memory.

Detects similar/duplicate EntityNode memories within a group and merges
them, keeping the core content while consolidating metadata.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from graphiti_core.nodes import EntityNode
from graphiti_core.utils.datetime_utils import utc_now


def _normalize(text: str) -> str:
    return ' '.join(text.lower().split())


def similarity(a: EntityNode, b: EntityNode, name_similarity: Callable[[str, str], float]) -> float:
    """Cosine-like name similarity proxy in [0, 1]."""
    if a.uuid == b.uuid:
        return 1.0
    return float(max(0.0, min(1.0, name_similarity(a.name, b.name))))


def find_duplicates(
    nodes: list[EntityNode],
    name_similarity: Callable[[str, str], float],
    threshold: float = 0.92,
) -> list[tuple[EntityNode, EntityNode]]:
    """Return pairs of nodes whose similarity exceeds ``threshold``."""
    pairs: list[tuple[EntityNode, EntityNode]] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if similarity(nodes[i], nodes[j], name_similarity) >= threshold:
                pairs.append((nodes[i], nodes[j]))
    return pairs


def merge_nodes(primary: EntityNode, duplicate: EntityNode) -> EntityNode:
    """Merge ``duplicate`` into ``primary``, keeping core content and
    consolidating metadata. Returns the updated ``primary``."""
    # Keep the higher importance and the richer summary.
    primary.importance_score = max(primary.importance_score, duplicate.importance_score)
    primary.access_count = primary.access_count + duplicate.access_count
    primary.feedback_score = max(primary.feedback_score, duplicate.feedback_score)
    if not primary.summary and duplicate.summary:
        primary.summary = duplicate.summary
    elif primary.summary and duplicate.summary and len(duplicate.summary) > len(primary.summary):
        primary.summary = duplicate.summary

    # Consolidate attributes (duplicate keys defer to primary).
    merged = dict(duplicate.attributes or {})
    merged.update(primary.attributes or {})
    primary.attributes = merged

    # Preserve the earliest creation time (original memory origin).
    if duplicate.created_at and (
        primary.created_at is None or duplicate.created_at < primary.created_at
    ):
        primary.created_at = duplicate.created_at

    primary.decay_enabled = primary.decay_enabled and duplicate.decay_enabled
    return primary


def consolidate_group(
    nodes: list[EntityNode],
    name_similarity: Callable[[str, str], float],
    threshold: float = 0.92,
    now: datetime | None = None,
) -> tuple[list[EntityNode], list[str]]:
    """Consolidate a group of nodes, returning surviving nodes and the list of
    merged-away node UUIDs."""
    now = now or utc_now()
    merged_uuids: list[str] = []
    survivors = list(nodes)

    changed = True
    while changed:
        changed = False
        pairs = find_duplicates(survivors, name_similarity, threshold)
        for primary, duplicate in pairs:
            if primary.uuid in merged_uuids or duplicate.uuid in merged_uuids:
                continue
            if primary.uuid == duplicate.uuid:
                continue
            merge_nodes(primary, duplicate)
            merged_uuids.append(duplicate.uuid)
            survivors = [n for n in survivors if n.uuid != duplicate.uuid]
            changed = True
            break

    return survivors, merged_uuids
