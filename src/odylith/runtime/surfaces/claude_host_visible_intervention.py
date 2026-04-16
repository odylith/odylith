"""Claude wrapper for assistant-rendered Odylith visible fallback."""

from __future__ import annotations

from odylith.runtime.surfaces import host_visible_intervention


def main(argv: list[str] | None = None) -> int:
    return host_visible_intervention.main_with_host("claude", argv)


if __name__ == "__main__":
    raise SystemExit(main())
