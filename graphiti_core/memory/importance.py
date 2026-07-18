"""
Memory Importance engine for Graphiti long-term agent memory.

Implements automatic importance scoring based on conversation frequency,
recency, and user feedback, plus gradual decay of stale, unused memories.
Protected (pinned) memories with ``decay_enabled = False`` never decay.
"""

from datetime import datetime, timedelta

from graphiti_core.nodes import EntityNode
from graphiti_core.utils.datetime_utils import utc_now

# Tunable weights for the importance composite.
FREQUENCY_WEIGHT = 0.35
RECENCY_WEIGHT = 0.30
FEEDBACK_WEIGHT = 0.35

# Decay configuration.
DECAY_HALF_LIFE_DAYS = 90.0
DECAY_ACCESS_PROTECTION = 5  # accesses below this count are eligible for decay


def _recency_factor(created_at: datetime, now: datetime | None = None) -> float:
    now = now or utc_now()
    age_days = max((now - created_at).total_seconds() / 86400.0, 0.0)
    # Exponential recency: 1.0 at creation, decaying toward 0 over time.
    return float(2.0 ** (-age_days / max(DECAY_HALF_LIFE_DAYS, 1e-6)))


def _frequency_factor(access_count: int) -> float:
    # Log-saturated frequency signal in [0, 1].
    if access_count <= 0:
        return 0.0
    return min(1.0, (access_count ** 0.5) / 5.0)


def compute_importance(
    node: EntityNode,
    frequency_weight: float = FREQUENCY_WEIGHT,
    recency_weight: float = RECENCY_WEIGHT,
    feedback_weight: float = FEEDBACK_WEIGHT,
    now: datetime | None = None,
) -> float:
    """Composite importance in [0, 1].

    importance = w_f * frequency + w_r * recency + w_fb * ((feedback + 1) / 2)
    """
    freq = _frequency_factor(node.access_count)
    rec = _recency_factor(node.created_at, now)
    feedback_norm = (max(min(node.feedback_score, 1.0), -1.0) + 1.0) / 2.0

    total_w = frequency_weight + recency_weight + feedback_weight
    if total_w <= 0:
        return 0.0

    score = (
        frequency_weight * freq
        + recency_weight * rec
        + feedback_weight * feedback_norm
    ) / total_w

    return max(0.0, min(1.0, score))


def apply_decay(
    node: EntityNode,
    now: datetime | None = None,
    half_life_days: float = DECAY_HALF_LIFE_DAYS,
) -> float:
    """Apply gradual time-based decay to ``importance_score``.

    Protected memories (``decay_enabled is False``) and memories with enough
    access activity are left untouched. Returns the (possibly) updated score.
    """
    now = now or utc_now()
    if not node.decay_enabled:
        return node.importance_score
    if node.access_count >= DECAY_ACCESS_PROTECTION:
        return node.importance_score

    age_days = max((now - node.created_at).total_seconds() / 86400.0, 0.0)
    decay_factor = 2.0 ** (-age_days / max(half_life_days, 1e-6))
    node.importance_score = max(0.0, min(1.0, node.importance_score * decay_factor))
    return node.importance_score


def recalculate_importance(
    node: EntityNode,
    apply_decay_first: bool = True,
    now: datetime | None = None,
) -> float:
    """Recompute the importance score for a single node.

    Optionally applies decay before recomputing the composite score.
    """
    now = now or utc_now()
    if apply_decay_first:
        apply_decay(node, now)
    node.importance_score = compute_importance(node, now=now)
    return node.importance_score


def register_access(node: EntityNode, now: datetime | None = None) -> None:
    """Record a retrieval/access event and refresh recency signals."""
    now = now or utc_now()
    node.access_count += 1
    node.last_accessed_at = now


def adjust_feedback(node: EntityNode, feedback: float) -> None:
    """Apply a user feedback signal in [-1, 1] (clamped)."""
    node.feedback_score = max(-1.0, min(1.0, feedback))


def decay_threshold() -> float:
    return DECAY_HALF_LIFE_DAYS
