"""Low-RAM-aware cache budgeting helpers for hot Odylith runtime paths.

The latency work in Odylith needs aggressive reuse without silently turning
process-local caches into an unbounded resident-memory tax. This module keeps
the policy explicit:

- detect a conservative normal vs low-RAM budget posture;
- estimate object sizes well enough for admission and eviction decisions; and
- provide one byte-budgeted segmented cache with TinyLFU-style admission so
  hot-path caches stay useful under pressure instead of growing forever.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from collections.abc import MutableMapping
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


_GIB = 1024 * 1024 * 1024
_MIB = 1024 * 1024
_LOW_RAM_TOTAL_BYTES = 8 * _GIB
_LOW_RAM_AVAILABLE_BYTES = int(1.5 * _GIB)
_LOW_RAM_HOT_PATH_BUDGET_BYTES = 24 * _MIB
_NORMAL_HOT_PATH_BUDGET_BYTES = 64 * _MIB
_LOW_RAM_SHOW_WORKING_BUDGET_BYTES = 32 * _MIB
_NORMAL_SHOW_WORKING_BUDGET_BYTES = 96 * _MIB
_DEFAULT_SKETCH_WIDTH = 2048
_DEFAULT_SKETCH_DEPTH = 4
_DEFAULT_PROTECTED_RATIO = 0.8
_POP_MISSING = object()


@dataclass(frozen=True, slots=True)
class MemoryStats:
    """Observed memory totals captured from the current host."""

    total_bytes: int | None
    available_bytes: int | None
    source: str
    detected: bool


@dataclass(frozen=True, slots=True)
class CacheBudgetPolicy:
    """Derived cache budgets for the current machine posture."""

    mode: str
    low_ram: bool
    memory: MemoryStats
    hot_path_budget_bytes: int
    show_working_budget_bytes: int

    @classmethod
    def detect(cls) -> "CacheBudgetPolicy":
        """Infer the cache-budget posture from the host's available memory."""
        memory = detect_memory_stats()
        low_ram = (
            not memory.detected
            or (memory.total_bytes is not None and memory.total_bytes <= _LOW_RAM_TOTAL_BYTES)
            or (
                memory.available_bytes is not None
                and memory.available_bytes < _LOW_RAM_AVAILABLE_BYTES
            )
        )
        return cls(
            mode="low_ram" if low_ram else "normal",
            low_ram=low_ram,
            memory=memory,
            hot_path_budget_bytes=(
                _LOW_RAM_HOT_PATH_BUDGET_BYTES if low_ram else _NORMAL_HOT_PATH_BUDGET_BYTES
            ),
            show_working_budget_bytes=(
                _LOW_RAM_SHOW_WORKING_BUDGET_BYTES
                if low_ram
                else _NORMAL_SHOW_WORKING_BUDGET_BYTES
            ),
        )


def detect_memory_stats() -> MemoryStats:
    """Probe the current host for total and available memory."""
    total_bytes, available_bytes, source = _sysconf_memory_bytes()
    if total_bytes is not None or available_bytes is not None:
        return MemoryStats(
            total_bytes=total_bytes,
            available_bytes=available_bytes,
            source=source or "sysconf",
            detected=True,
        )
    total_bytes, available_bytes, source = _darwin_memory_bytes()
    if total_bytes is not None or available_bytes is not None:
        return MemoryStats(
            total_bytes=total_bytes,
            available_bytes=available_bytes,
            source=source or "darwin",
            detected=True,
        )
    return MemoryStats(
        total_bytes=None,
        available_bytes=None,
        source="unknown",
        detected=False,
    )


def _sysconf_memory_bytes() -> tuple[int | None, int | None, str]:
    """Read memory information from POSIX `sysconf` when available."""
    page_size = _sysconf_int("SC_PAGE_SIZE") or _sysconf_int("SC_PAGESIZE")
    total_pages = _sysconf_int("SC_PHYS_PAGES")
    avail_pages = _sysconf_int("SC_AVPHYS_PAGES")
    if page_size is None or total_pages is None:
        return (None, None if avail_pages is None else 0, "")
    total_bytes = total_pages * page_size
    available_bytes = avail_pages * page_size if avail_pages is not None else None
    return (total_bytes, available_bytes, "sysconf")


def _sysconf_int(name: str) -> int | None:
    """Best-effort wrapper around `os.sysconf` for integer values."""
    try:
        return int(os.sysconf(name))
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _darwin_memory_bytes() -> tuple[int | None, int | None, str]:
    """Read memory information from Darwin-specific tooling."""
    if sys.platform != "darwin":
        return (None, None, "")
    total_bytes = _sysctl_int("hw.memsize")
    available_bytes = None
    vm_stat = _run_command(["vm_stat"])
    if vm_stat:
        page_size = 4096
        for line in vm_stat.splitlines():
            stripped = line.strip()
            if stripped.startswith("Mach Virtual Memory Statistics:"):
                parts = stripped.split("page size of")
                if len(parts) == 2:
                    token = parts[1].strip().split(" ", 1)[0]
                    try:
                        page_size = int(token)
                    except ValueError:
                        page_size = 4096
                continue
        free_pages = 0
        speculative_pages = 0
        inactive_pages = 0
        for line in vm_stat.splitlines():
            if ":" not in line:
                continue
            label, raw_value = line.split(":", 1)
            digits = "".join(ch for ch in raw_value if ch.isdigit())
            if not digits:
                continue
            value = int(digits)
            normalized = label.strip().lower()
            if normalized == "pages free":
                free_pages = value
            elif normalized == "pages speculative":
                speculative_pages = value
            elif normalized == "pages inactive":
                inactive_pages = value
        available_bytes = (free_pages + speculative_pages + inactive_pages) * page_size
    if total_bytes is None and available_bytes is None:
        return (None, None, "")
    return (total_bytes, available_bytes, "darwin")


def _sysctl_int(key: str) -> int | None:
    """Read a single integer-valued sysctl key."""
    output = _run_command(["sysctl", "-n", key])
    if not output:
        return None
    try:
        return int(output.strip())
    except ValueError:
        return None


def _run_command(argv: list[str]) -> str:
    """Run a short-lived subprocess and return trimmed stdout on success."""
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    return str(completed.stdout or "").strip()


def estimate_object_size_bytes(value: Any, *, max_depth: int = 4) -> int:
    """Approximate the resident size of a Python object graph."""
    seen: set[int] = set()
    return _estimate(value, seen=seen, depth=max_depth)


def _estimate(value: Any, *, seen: set[int], depth: int) -> int:
    """Recursively estimate object size while avoiding repeated references."""
    if depth < 0:
        return 0
    object_id = id(value)
    if object_id in seen:
        return 0
    seen.add(object_id)
    size = sys.getsizeof(value)
    if depth == 0:
        return size
    if isinstance(value, dict):
        for key, item in value.items():
            size += _estimate(key, seen=seen, depth=depth - 1)
            size += _estimate(item, seen=seen, depth=depth - 1)
        return size
    if isinstance(value, (list, tuple, set, frozenset, OrderedDict)):
        for item in value:
            size += _estimate(item, seen=seen, depth=depth - 1)
        return size
    if isinstance(value, Path):
        return size + len(str(value))
    return size


@dataclass(slots=True)
class _CacheEntry:
    """Cache resident carrying the stored value and its estimated byte cost."""

    key: Any
    value: Any
    size_bytes: int


class ByteBudgetedSegmentedCache(MutableMapping[Any, Any]):
    """A byte-budgeted probation/protected cache with TinyLFU-style admission.

    The cache uses two SLRU segments:
    - probation for newly admitted entries
    - protected for entries with at least one confirmed hit

    Admission is guarded by a compact count-min sketch. When the cache is full,
    a new item only displaces the oldest probation resident if its frequency
    estimate is at least as strong.
    """

    def __init__(
        self,
        *,
        name: str,
        max_bytes: int,
        protected_ratio: float = _DEFAULT_PROTECTED_RATIO,
        sketch_width: int = _DEFAULT_SKETCH_WIDTH,
        sketch_depth: int = _DEFAULT_SKETCH_DEPTH,
    ) -> None:
        self.name = str(name).strip() or "cache"
        self.max_bytes = max(0, int(max_bytes))
        self.protected_ratio = min(max(float(protected_ratio), 0.1), 0.95)
        self._probation: OrderedDict[Any, _CacheEntry] = OrderedDict()
        self._protected: OrderedDict[Any, _CacheEntry] = OrderedDict()
        self._bytes = 0
        self._sketch_width = max(64, int(sketch_width))
        self._sketch_depth = max(2, int(sketch_depth))
        self._sketch = [[0] * self._sketch_width for _ in range(self._sketch_depth)]

    @property
    def current_bytes(self) -> int:
        """Return the cache's current estimated resident size."""
        return int(self._bytes)

    def __getitem__(self, key: Any) -> Any:
        entry = self._lookup_entry(key)
        if entry is None:
            raise KeyError(key)
        self._record_access(key)
        self._promote_on_hit(key)
        return entry.value

    def __setitem__(self, key: Any, value: Any) -> None:
        size_bytes = estimate_object_size_bytes((key, value))
        self.set_with_size(key, value, size_bytes=size_bytes)

    def set_with_size(self, key: Any, value: Any, *, size_bytes: int) -> bool:
        """Insert or update an entry when the caller already knows its byte size."""
        normalized_size = max(0, int(size_bytes))
        if self.max_bytes <= 0 or normalized_size > self.max_bytes:
            self.pop(key, None)
            return False
        existing = self._lookup_entry(key)
        self._record_access(key)
        if existing is not None:
            self._bytes -= existing.size_bytes
            existing.value = value
            existing.size_bytes = normalized_size
            self._bytes += normalized_size
            self._promote_on_hit(key)
            self._evict_while_over_budget(incoming_key=key)
            return True
        if not self._admit_new_entry(key=key, size_bytes=normalized_size):
            return False
        entry = _CacheEntry(key=key, value=value, size_bytes=normalized_size)
        self._probation[key] = entry
        self._probation.move_to_end(key)
        self._bytes += normalized_size
        self._evict_while_over_budget(incoming_key=key)
        return key in self

    def __delitem__(self, key: Any) -> None:
        if key in self._protected:
            entry = self._protected.pop(key)
            self._bytes -= entry.size_bytes
            return
        if key in self._probation:
            entry = self._probation.pop(key)
            self._bytes -= entry.size_bytes
            return
        raise KeyError(key)

    def __iter__(self) -> Iterator[Any]:
        for key in self._protected:
            yield key
        for key in self._probation:
            if key not in self._protected:
                yield key

    def __len__(self) -> int:
        return len(self._protected) + len(self._probation)

    def get(self, key: Any, default: Any = None) -> Any:
        """Return a cached value and treat the lookup as an access hit."""
        entry = self._lookup_entry(key)
        if entry is None:
            return default
        self._record_access(key)
        self._promote_on_hit(key)
        return entry.value

    def pop(self, key: Any, default: Any = _POP_MISSING) -> Any:
        """Remove and return one cache entry."""
        if key in self._protected:
            entry = self._protected.pop(key)
            self._bytes -= entry.size_bytes
            return entry.value
        if key in self._probation:
            entry = self._probation.pop(key)
            self._bytes -= entry.size_bytes
            return entry.value
        if default is not _POP_MISSING:
            return default
        raise KeyError(key)

    def clear(self) -> None:
        """Drop every cached entry and reset the accounted byte total."""
        self._probation.clear()
        self._protected.clear()
        self._bytes = 0

    def _lookup_entry(self, key: Any) -> _CacheEntry | None:
        """Return the resident entry from either segment without mutating state."""
        entry = self._protected.get(key)
        if entry is not None:
            return entry
        return self._probation.get(key)

    def _record_access(self, key: Any) -> None:
        """Increment the compact frequency sketch for the given key."""
        for depth in range(self._sketch_depth):
            index = hash((depth, key)) % self._sketch_width
            bucket = self._sketch[depth][index]
            if bucket < 255:
                self._sketch[depth][index] = bucket + 1

    def _estimate_frequency(self, key: Any) -> int:
        """Estimate how frequently a key has been seen by the admission sketch."""
        return min(
            self._sketch[depth][hash((depth, key)) % self._sketch_width]
            for depth in range(self._sketch_depth)
        )

    def _admit_new_entry(self, *, key: Any, size_bytes: int) -> bool:
        """Decide whether a new entry is worth admitting under pressure."""
        if self._bytes + size_bytes <= self.max_bytes:
            return True
        victim = self._oldest_probation_key()
        if victim is None:
            return True
        incoming_freq = self._estimate_frequency(key)
        victim_freq = self._estimate_frequency(victim)
        return incoming_freq >= victim_freq

    def _protected_byte_budget(self) -> int:
        """Return the target byte budget for the protected segment."""
        return int(self.max_bytes * self.protected_ratio)

    def _probation_byte_budget(self) -> int:
        """Return the target byte budget for the probation segment."""
        return max(0, self.max_bytes - self._protected_byte_budget())

    def _promote_on_hit(self, key: Any) -> None:
        """Promote a probation resident into the protected segment after a hit."""
        if key in self._protected:
            self._protected.move_to_end(key)
            return
        entry = self._probation.pop(key, None)
        if entry is None:
            return
        self._protected[key] = entry
        self._protected.move_to_end(key)
        while self._segment_bytes(self._protected) > self._protected_byte_budget() and self._protected:
            demote_key, demote_entry = self._protected.popitem(last=False)
            self._probation[demote_key] = demote_entry
            self._probation.move_to_end(demote_key)
        self._evict_probation_until_budget()

    def _oldest_probation_key(self) -> Any | None:
        """Return the oldest probation key, if any."""
        for token in self._probation:
            return token
        return None

    def _evict_probation_until_budget(self) -> None:
        """Trim probation entries until the segment fits its byte budget."""
        while self._segment_bytes(self._probation) > self._probation_byte_budget() and self._probation:
            _key, entry = self._probation.popitem(last=False)
            self._bytes -= entry.size_bytes

    def _evict_while_over_budget(self, *, incoming_key: Any) -> None:
        """Evict entries until total resident bytes are back under budget."""
        while self._bytes > self.max_bytes:
            victim_key = self._oldest_probation_key()
            if victim_key is not None and victim_key != incoming_key:
                victim = self._probation.pop(victim_key)
                self._bytes -= victim.size_bytes
                continue
            if self._probation and incoming_key in self._probation and len(self._probation) > 1:
                victim_key = next(key for key in self._probation if key != incoming_key)
                victim = self._probation.pop(victim_key)
                self._bytes -= victim.size_bytes
                continue
            if self._protected:
                _victim_key, victim = self._protected.popitem(last=False)
                self._bytes -= victim.size_bytes
                continue
            if incoming_key in self._probation:
                victim = self._probation.pop(incoming_key)
                self._bytes -= victim.size_bytes
            break
        self._evict_probation_until_budget()

    @staticmethod
    def _segment_bytes(entries: OrderedDict[Any, _CacheEntry]) -> int:
        """Sum the tracked resident bytes for one cache segment."""
        return sum(entry.size_bytes for entry in entries.values())


def scaled_cache_budget_bytes(*, base_budget_bytes: int, numerator: int, denominator: int = 100) -> int:
    """Scale a base cache budget while enforcing a small practical floor."""
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    return max(256 * 1024, int(base_budget_bytes * max(0, numerator) / denominator))


__all__ = [
    "ByteBudgetedSegmentedCache",
    "CacheBudgetPolicy",
    "MemoryStats",
    "detect_memory_stats",
    "estimate_object_size_bytes",
    "scaled_cache_budget_bytes",
]
