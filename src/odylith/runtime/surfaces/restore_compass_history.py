"""Restore archived Compass history snapshots back into the active history lane."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from odylith.runtime.surfaces import compass_dashboard_runtime
from odylith.runtime.surfaces import render_compass_dashboard


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith compass restore-history",
        description="Restore archived Compass daily history snapshots into active history.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--runtime-dir",
        default="odylith/compass/runtime",
        help="Compass runtime snapshot directory.",
    )
    parser.add_argument(
        "--date",
        action="append",
        default=[],
        help="Archived Compass history date to restore (`YYYY-MM-DD`). Repeatable.",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip Compass surface refresh after restoring history files.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    runtime_dir = _resolve(repo_root, str(args.runtime_dir))

    try:
        restored, already_active, pins_path = compass_dashboard_runtime.restore_archived_history_dates(
            repo_root=repo_root,
            runtime_dir=runtime_dir,
            dates=list(args.date),
        )
    except ValueError as exc:
        print("restore compass history FAILED")
        print(f"- {exc}")
        return 2
    except Exception as exc:
        print("restore compass history FAILED")
        print(f"- {exc}")
        return 1

    if not args.no_render:
        retention_days = compass_dashboard_runtime.load_history_retention_days(runtime_dir=runtime_dir)
        rc = render_compass_dashboard.main(
            [
                "--repo-root",
                str(repo_root),
                "--runtime-dir",
                str(runtime_dir),
                "--retention-days",
                str(retention_days),
            ]
        )
        if rc != 0:
            print("restore compass history FAILED")
            print("- archive files were restored and pinned, but Compass render failed")
            return rc

    print("restore compass history passed")
    print(f"- runtime_dir: {runtime_dir}")
    print(f"- restored: {', '.join(restored) if restored else '(none)'}")
    print(f"- already_active: {', '.join(already_active) if already_active else '(none)'}")
    print(f"- restore_pins: {pins_path}")
    print(f"- render_refreshed: {'no' if args.no_render else 'yes'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
