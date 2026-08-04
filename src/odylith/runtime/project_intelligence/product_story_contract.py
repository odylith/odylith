"""Typed semantic-slot contract for Project Product Story cards."""

from __future__ import annotations


PRODUCT_STORY_CARD_SLOTS = (
    ("User Problem", "user_problem"),
    ("First Path", "first_path"),
    ("Product Boundary", "product_boundary"),
    ("Owned Capabilities", "owned_capabilities"),
    ("Proof", "proof"),
)
PRODUCT_STORY_SLOT_BY_LABEL = dict(PRODUCT_STORY_CARD_SLOTS)


__all__ = ["PRODUCT_STORY_CARD_SLOTS", "PRODUCT_STORY_SLOT_BY_LABEL"]
