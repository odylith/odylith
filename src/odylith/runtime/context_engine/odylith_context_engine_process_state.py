"""Shared process-local caches for context-engine runtime slices.

These caches are intentionally process-scoped and shared across hot-path,
projection, and memory/runtime-learning helpers. Centralizing them here keeps
the ownership explicit without forcing import-time reach-through into the
context-engine store.
"""

from __future__ import annotations

from odylith.runtime.context_engine import runtime_read_session


_PROCESS_WARM_CACHE_TTL_SECONDS = 300.0
_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE_TTL_SECONDS = 60.0
_PROCESS_WARM_CACHE: dict[str, float] = {}
_PROCESS_WARM_CACHE_FINGERPRINTS: dict[str, str] = {}
_PROCESS_PROJECTION_ROWS_CACHE = runtime_read_session.shared_process_cache_view("projection_rows")
_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE = runtime_read_session.shared_process_cache_view("optimization_snapshot")
_PROCESS_MISS_RECOVERY_INDEX_CACHE = runtime_read_session.shared_process_cache_view("miss_recovery_index")
_PROCESS_PATH_SCOPE_CACHE = runtime_read_session.shared_process_cache_view("path_scope")
_PROCESS_PATH_SIGNAL_PROFILE_CACHE = runtime_read_session.shared_process_cache_view("path_signal_profile")
_PROCESS_ARCHITECTURE_PACKET_CACHE = runtime_read_session.shared_process_cache_view("architecture_packet")
_PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE = runtime_read_session.shared_process_cache_view("orchestration_adoption")
_PROCESS_JUDGMENT_MEMORY_SNAPSHOT_CACHE = runtime_read_session.shared_process_cache_view("judgment_memory")
_PROCESS_GIT_REF_CACHE = runtime_read_session.shared_process_cache_view("git_ref")
_PROCESS_PROJECTION_CONNECTION_CACHE = runtime_read_session.shared_process_cache_view("projection_connection")
_PROCESS_GIT_REF_CACHE_TTL_SECONDS = 5.0


__all__ = [
    "_PROCESS_ARCHITECTURE_PACKET_CACHE",
    "_PROCESS_GIT_REF_CACHE",
    "_PROCESS_GIT_REF_CACHE_TTL_SECONDS",
    "_PROCESS_JUDGMENT_MEMORY_SNAPSHOT_CACHE",
    "_PROCESS_MISS_RECOVERY_INDEX_CACHE",
    "_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE",
    "_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE_TTL_SECONDS",
    "_PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE",
    "_PROCESS_PATH_SCOPE_CACHE",
    "_PROCESS_PATH_SIGNAL_PROFILE_CACHE",
    "_PROCESS_PROJECTION_CONNECTION_CACHE",
    "_PROCESS_PROJECTION_ROWS_CACHE",
    "_PROCESS_WARM_CACHE",
    "_PROCESS_WARM_CACHE_FINGERPRINTS",
    "_PROCESS_WARM_CACHE_TTL_SECONDS",
]
