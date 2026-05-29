"""Runtime adapters for feeding external agent events into Canonical CAT."""

from .base import CATAdapter
from .codex_adapter import CodexAdapter

__all__ = ["CATAdapter", "CodexAdapter"]
