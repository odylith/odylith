# Operating Model

Odylith owns product guidance, skills, and execution helpers under `odylith/`.

Across consumer-facing Odylith work, the normal posture is Odylith-first:
start with Odylith packets, surfaces, CLI workflows, and routed execution,
then widen to direct `rg`, source reads, or standalone host search only when
Odylith reports ambiguity, missing anchors, repair conditions, or explicit
fallback.

The surrounding repository stays the source of truth for its own code, plans,
bugs, and docs outside that tree. Odylith accelerates access to that truth; it
does not replace the tracked markdown or JSON authority.
