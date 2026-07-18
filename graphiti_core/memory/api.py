"""
MemoryManager: long-term agent memory API for Graphiti.

Wraps the new memory engine (importance, decay, consolidation, hybrid ranking,
statistics) on top of an existing :class:`graphiti_core.graphiti.Graphiti`
instance. The base Graphiti API is left unchanged; this manager adds the
memory-specific operations requested.

New public operations:
  - get_importance(node_uuid)            -> importance score
  - recalculate_importance(node_uuids)  -> recomputed scores
  - consolidate_memories(group_id)      -> merged node uuids
  - get_memory_statistics(group_id)     -> aggregate stats
"""

from datetime import datetime
from typing import Any

from graphiti_core.graphiti import Graphiti
from graphiti_core.memory.consolidation import consolidate_group
from graphiti_core.memory.hybrid_ranking import rank_nodes
from graphiti_core.memory.importance import (
    adjust_feedback,
    apply_decay,
    recalculate_importance,
    register_access,
)
from graphiti_core.nodes import EntityNode


class MemoryManager:
    def __init__(self, graphiti: Graphiti):
        self.graphiti = graphiti

    @property
    def driver(self):
        return self.graphiti.driver

    async def get_importance(self, node_uuid: str) -> float:
        """Return the current importance score of a memory node."""
        node = await EntityNode.get_by_uuid(self.driver, node_uuid)
        return node.importance_score

    async def recalculate_importance(
        self,
        node_uuids: list[str] | None = None,
        group_ids: list[str] | None = None,
        apply_decay_first: bool = True,
        now: datetime | None = None,
    ) -> dict[str, float]:
        """Recompute importance for the given nodes (or an entire group).

        Returns a mapping of node uuid -> new importance score.
        """
        if node_uuids:
            nodes = [await EntityNode.get_by_uuid(self.driver, u) for u in node_uuids]
        elif group_ids:
            nodes = await EntityNode.get_by_group_ids(self.driver, group_ids)
        else:
            nodes = []

        results: dict[str, float] = {}
        for node in nodes:
            score = recalculate_importance(node, apply_decay_first, now)
            await node.save(self.driver)
            results[node.uuid] = score
        return results

    async def apply_decay_all(
        self, group_ids: list[str] | None = None, now: datetime | None = None
    ) -> dict[str, float]:
        """Apply memory decay to all (or group-scoped) nodes."""
        nodes = (
            await EntityNode.get_by_group_ids(self.driver, group_ids)
            if group_ids
            else await EntityNode.get_by_group_ids(self.driver, [self.graphiti.group_id])
            if getattr(self.graphiti, 'group_id', None)
            else []
        )
        results: dict[str, float] = {}
        for node in nodes:
            score = apply_decay(node, now)
            await node.save(self.driver)
            results[node.uuid] = score
        return results

    async def record_access(self, node_uuid: str, now: datetime | None = None) -> float:
        """Register a retrieval/access event and persist."""
        node = await EntityNode.get_by_uuid(self.driver, node_uuid)
        register_access(node, now)
        await node.save(self.driver)
        return node.importance_score

    async def set_feedback(self, node_uuid: str, feedback: float) -> float:
        """Apply a user feedback signal in [-1, 1] and persist."""
        node = await EntityNode.get_by_uuid(self.driver, node_uuid)
        adjust_feedback(node, feedback)
        await node.save(self.driver)
        return node.feedback_score

    async def consolidate_memories(
        self,
        group_id: str,
        name_similarity,
        threshold: float = 0.92,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Merge similar/duplicate memories in a group.

        Returns a dict with ``survivors`` (uuids) and ``merged`` (uuids).
        """
        nodes = await EntityNode.get_by_group_ids(self.driver, [group_id])
        survivors, merged_uuids = consolidate_group(
            nodes, name_similarity, threshold, now
        )
        # Persist survivors (merged attributes/importance) and delete merged-away.
        for node in survivors:
            await node.save(self.driver)
        if merged_uuids:
            await EntityNode.delete_by_uuids(self.driver, merged_uuids)
        return {
            'survivors': [n.uuid for n in survivors],
            'merged': merged_uuids,
        }

    async def get_memory_statistics(self, group_id: str) -> dict[str, Any]:
        """Aggregate memory statistics for a group."""
        nodes = await EntityNode.get_by_group_ids(self.driver, [group_id])
        if not nodes:
            return {
                'group_id': group_id,
                'node_count': 0,
                'avg_importance': 0.0,
                'protected_count': 0,
                'total_access': 0,
                'max_importance': 0.0,
                'min_importance': 0.0,
            }
        scores = [n.importance_score for n in nodes]
        return {
            'group_id': group_id,
            'node_count': len(nodes),
            'avg_importance': sum(scores) / len(scores),
            'max_importance': max(scores),
            'min_importance': min(scores),
            'protected_count': sum(1 for n in nodes if not n.decay_enabled),
            'total_access': sum(n.access_count for n in nodes),
        }

    async def hybrid_rank(
        self,
        candidates: list[tuple[EntityNode, float]],
        edges_by_uuid: dict[str, list[Any]] | None = None,
        limit: int | None = None,
        now: datetime | None = None,
    ) -> list[tuple[EntityNode, float]]:
        """Rank candidate (node, vector_similarity) pairs with the hybrid score."""
        return rank_nodes(candidates, edges_by_uuid, now=now, limit=limit)
