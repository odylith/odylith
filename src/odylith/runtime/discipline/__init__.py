"""Public entrypoints for the Odylith Discipline runtime package.

The package is deliberately exported through a narrow surface so callers do not
need to understand the internal split between signals, laws, pressure,
affordances, proof, learning, and memory.
"""

from odylith.runtime.discipline.decision import evaluate_discipline_move

__all__ = ["evaluate_discipline_move"]
