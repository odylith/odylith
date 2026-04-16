"""Claude wrapper for Odylith intervention activation status."""

from __future__ import annotations

from odylith.runtime.surfaces import host_intervention_status


def main(argv: list[str] | None = None) -> int:
    return host_intervention_status.main_with_host("claude", argv)


if __name__ == "__main__":
    raise SystemExit(main())
