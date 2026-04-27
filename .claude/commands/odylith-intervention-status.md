---
description: Show whether Odylith Observations, Proposals, Ambient beats, and Assist are active in this Claude chat.
argument-hint: [--session-id SESSION] [--json]
---

Show the low-latency Odylith intervention status for this Claude project.

Forwarded flags (from user): `$ARGUMENTS`

1. Run `./.odylith/bin/odylith claude intervention-status --repo-root . $ARGUMENTS`.
2. Read the readiness checks and active UX lanes before claiming intervention output is live in this chat.
3. If the status says no visible Odylith beat has been recorded for this session, run the printed `visible-intervention` smoke command and show that Markdown directly.
4. Do not treat hook payload generation, compatibility output, or hidden additional context as proof that the user saw an Observation, Proposal, Ambient beat, or Assist.
