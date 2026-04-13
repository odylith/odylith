# Execution Engine

The execution engine answers one question:
**"given what we know is true, what is the next admissible move?"**

It sits between the Context Engine, which answers "what is true and relevant?",
and the actual tool invocation layer. It never executes anything itself. It
produces a machine-readable contract that tells the agent what it can and
cannot do.

## Pipeline

1. **Detect the host**  
   Determine whether the active host is Codex or Claude Code, including its
   delegation style, model family, and capabilities. This becomes
   `ExecutionHostProfile`.

2. **Build the contract**  
   From the grounded context packet, assemble a single `ExecutionContract`
   containing the objective, target scope, allowed and forbidden moves,
   success criteria, validation plan, external dependencies, and critical
   path.

3. **Promote hard constraints**  
   User corrections such as "don't use X" or "only touch Y" are promoted into
   `HardConstraint` records so later heuristics cannot override them.

4. **Detect contradictions**  
   Compare the intended action against the contract, user instructions, docs,
   and live state. If the action conflicts with any of them, emit a
   `ContradictionRecord` with severity and a blocking flag.

5. **Classify resource closure**  
   Decide whether the requested scope is safe, incomplete because dependencies
   are missing, or destructive because it partially overlaps a destructive
   group. This stops the agent from editing half of a coupled set.

6. **Normalize external dependencies**  
   If there is an in-flight CI run, deploy, or callback, normalize its status
   and produce a `SemanticReceipt` with a resume token so the agent reattaches
   instead of starting over.

7. **Shape the event stream**  
   Contradictions, unsafe closures, active waits, history-rule pressure, and
   context pressure are shaped into an append-only `ExecutionEvent` stream.

8. **Derive the frontier**  
   Walk the event stream to produce `ExecutionFrontier`: the current phase,
   last successful phase, active blocker, in-flight external IDs, resume
   handles, and the truthful next move.

9. **Evaluate admissibility**  
   Screen the intended action against everything above. The outcome is one of:
   - `admit`: proceed
   - `deny`: the action is not allowed; return the nearest admissible
     alternative
   - `defer`: the action is premature; resolve the blocker first

   The decision also carries violated preconditions, pressure signals,
   re-anchor requirements, and host-specific hints.

10. **Synthesize validation matrix**  
    Derive the minimum set of checks, such as deploy, verify, recover, and
    CRUD, that the agent must pass before the work is done.

11. **Guard delegation and parallelism**  
    `LaneGovernanceGuard` consumes the compact governance summary and blocks
    delegation or parallel fan-out when the frontier says re-anchor, wait,
    verify or recover, unsafe closure, or the host cannot support it.

## What It Does Not Do

- It does not ground truth from the repo. That is the Context Engine.
- It does not diagnose why the posture exists. That is Tribunal.
- It does not decide scope or operator readout. That is Delivery Intelligence.
- It does not invoke tools or run commands. The caller does that.
- It does not own the delegation transport. Router and Orchestrator do.

## Design Principle

The contract is **host-general first**. Codex and Claude Code share the same
policy surface: the same admissibility rules, frontier derivation, and closure
classification.

Host-specific behavior, including delegation style, model selection, interrupt
capability, and artifact paths, is additive and capability-gated through the
execution profile. It is never baked into the shared contract.
