from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


class _DeleteMarker:
    """Sentinel object used to represent 'delete this key' semantics."""


# Public sentinel for delete semantics.
DELETE = _DeleteMarker()


@dataclass(frozen=True)
class Explanation:
    final_value: Any
    source: Literal["base", "env", "override", "missing"]
    overridden: bool
    override_chain: list[str]


def explain_config_value(
    key: str,
    base: dict,
    env: dict,
    override: dict,
) -> Explanation:
    """
    Implement Config Diff Explanation for a single (possibly nested) key.

    NOTE:
    - This function is intentionally left incorrect.
    - The agent must implement this function to satisfy the test suite.
    """
    # BASELINE PLACEHOLDER (INTENTIONALLY INCORRECT)
    return Explanation(
        final_value=None,
        source="missing",
        overridden=False,
        override_chain=[],
    )
