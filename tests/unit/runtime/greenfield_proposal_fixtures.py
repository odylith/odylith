"""Graph-native transaction fixture helpers.

Legacy proposal interpretation fixtures were deleted with their parser authority.
This module retains only sealed-byte transaction custody used by commit-law tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    load_sealed_product_create_commit,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    write_compiled_product_create_transaction_file,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    semantic_intent_with_authority,
)


def compiled_graph_transaction(repo_root: Path) -> Any:
    """Compile the canonical v2 graph fixture through the public graph workflow."""

    intent = semantic_intent_with_authority()
    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    proposal = build_verified_semantic_proposal_for_repo(
        repo_root=repo_root,
        authority=authority,
        release_selector="0.0.1",
    )
    return compile_verified_semantic_transaction(
        repo_root=repo_root,
        proposal=proposal,
        intent_authority=authority,
        release_selector="0.0.1",
    )


def seal_compiled_greenfield_transaction(*, repo_root: Path, transaction: Any) -> Any:
    """Persist and reload the exact receipt-bound graph transaction."""

    path = (
        Path(repo_root)
        / ".odylith/runtime/greenfield/test-product-create-transaction.v1.json"
    )
    write_compiled_product_create_transaction_file(path, transaction)
    return load_sealed_product_create_commit(path)
