"""CLI argument parsing for the Casebook dashboard renderer."""

from __future__ import annotations

import argparse
from typing import Sequence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Render odylith/casebook/casebook.html from the bug knowledge base.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="odylith/casebook/casebook.html")
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime projection store when available for bug rows.",
    )
    return parser.parse_args(argv)
