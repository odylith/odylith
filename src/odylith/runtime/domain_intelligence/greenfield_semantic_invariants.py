"""Stable semantic role definitions for one-pass Greenfield authoring."""

TITLE_ROLE_DEFINITION = (
    "A source-cited name or concise label for the requested product, workflow, or "
    "product state. Identify what the request asks to create, operate, or review; "
    "do not substitute source or evidence metadata such as a repository, fixture, "
    "dataset, or artifact merely because it is named. When source evidence names "
    "such metadata alongside a distinct requested workflow, title the requested "
    "workflow instead. A repository or artifact name remains valid when the source "
    "explicitly makes that named repository or artifact itself the requested product "
    "identity, rather than evidence for a different requested product."
)
STATE_OBJECT_ROLE_DEFINITION = (
    "One source-cited subject, entity, record, work item, case, artifact, or status "
    "whose state the workflow changes or reviews. The subject may be a person; never "
    "select a performer merely because it performs the action, or select a workflow "
    "sequence, location, goal, or entire product description."
)
PROOF_BOUNDARY_ROLE_DEFINITION = (
    "A source span identifying observable evidence, an output, or a reviewable "
    "state that can prove the first path worked. It may be a phrase or complete "
    "statement; prefer concise wording but do not reject a longer faithful span. "
    "An activity, workflow stage, goal, product label, or purpose without an "
    "identified result is not proof."
)
INTERNAL_SYSTEM_ROLE_DEFINITION = (
    "A source-named product-owned system or component. The whole named product "
    "may be both the title and an internal-system alias when source context "
    "establishes that product owner; this is the same owner, not a new component. "
    "Do not infer product ownership from a mere mention of an external "
    "organization, human role, or arbitrary label."
)
OPERATIONAL_CONSTRAINT_ROLE_DEFINITION = (
    "A complete source-stated requirement, prohibition, permission or ordering constraint. "
    "It must govern the requested product or its requested governance or delivery outcome. "
    "An ordinary product capability description alone is not an operational constraint; "
    "retain actual operating obligations, exclusions and conditions, including those "
    "stated alongside a capability. Each quote is projected independently: retain any "
    "source-stated governed subject, required, prohibited or permitted behavior and any "
    "condition or scope that changes its meaning. Include exact contiguous source context "
    "before or after when needed; a fragment whose subject or applicability can only be "
    "recovered from surrounding source is insufficient. Do not require an explicit subject "
    "for a complete impersonal or imperative source constraint. A directive that governs "
    "the supplied source evidence, fixture, or candidate as an input to this authoring "
    "transaction—including its identity, metadata, handling, projection, or exclusion from "
    "product copy—is a source-custody control: obey it by leaving it in sealed source "
    "evidence, not by selecting or restating it as a product fact or proposed product work. "
    "Do not apply that exclusion to a requested product workflow that manages evidence, "
    "provenance, or source identity as domain data. Classify by the directive's actual "
    "governed system and outcome. Prefer a concise self-contained span, without inventing "
    "actors, relations or restrictions absent from the source."
)
HUMAN_ACTOR_ROLE_DEFINITION = (
    "Source-stated people or human roles participating in the product, including "
    "source-stated beneficiaries and explicit output recipients outside the first path. "
    "Participation does not establish a performing actor or direct product operator; "
    "do not assign those roles without source support. The audience for a request, brief, "
    "report, proposal, or other authoring deliverable is not thereby a product participant; "
    "include that audience only when the source separately states that it uses, benefits "
    "from, participates in, or receives an output from the requested product. When a direct "
    "workflow names its actor, do not promote a broader authoring audience into that "
    "workflow. Use an empty list when no human participant is stated. An activity, artifact, "
    "or output-purpose modifier is not a human participant."
)
PRODUCT_STORY_ROLE_DEFINITION = (
    "A complete source span about product behavior or outcome, excluding the operator "
    "request to create a proposal or product and excluding a title or category label."
)
REFERENCE_PROVENANCE_ROLE_CONTRACT = (
    "Interpret each part of the evidence by its semantic role, independent of label order "
    "or shared vocabulary. When the evidence supplies a complete requested workflow with "
    "a source-supported participant or task owner, usable task and visible result, that "
    "workflow remains the product-intent authority. Separately identified reference "
    "provenance—including a source artifact, repository or reference-system description—"
    "is grounding context, not a competing product boundary, unless the request explicitly "
    "assigns that reference an owned role, dependency, constraint or result in the requested "
    "workflow. A thematic difference between the requested workflow and reference context "
    "is not material ambiguity by itself. Ask for product_boundary only when the source "
    "itself leaves materially competing or unclear inside-versus-outside responsibility, "
    "dependency or scope limits that cannot safely remain an explicit assumption; the "
    "workflow need not be incomplete for that boundary to be material."
)


__all__ = [
    "HUMAN_ACTOR_ROLE_DEFINITION",
    "INTERNAL_SYSTEM_ROLE_DEFINITION",
    "OPERATIONAL_CONSTRAINT_ROLE_DEFINITION",
    "PRODUCT_STORY_ROLE_DEFINITION",
    "PROOF_BOUNDARY_ROLE_DEFINITION",
    "REFERENCE_PROVENANCE_ROLE_CONTRACT",
    "STATE_OBJECT_ROLE_DEFINITION",
    "TITLE_ROLE_DEFINITION",
]
