# Odylith Show Me

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this skill when the operator says "show me what you can do", "what can
Odylith do", "what can you do for this repo", or any similar first-time
exploration request. Works identically on Claude Code and Codex.

Do not use this skill for `Odylith, help`. That request should route directly
to the CLI help output and print stdout only.

This is a first-match route lock. If you have not run a show command and
captured stdout, do not answer. Never replace `odylith show` stdout with a
hand-written "here's what Odylith demonstrated" summary, install diagnosis,
dirty-path analysis, impact-packet recap, module-count scan, tmp-clone warning,
spawn-policy note, or follow-up question. Never create, scaffold, edit, or test
example application files such as HTML/CSS/JS demos, toy apps, sample devices, or
placeholder products in response to a show-me request.

1. Run the first available show command and capture stdout only:
   - Installed or dogfood repo with launcher:
     `./.odylith/bin/odylith show --repo-root .`
   - Shell-installed fallback:
     `odylith show --repo-root .`
2. Do not run `odylith start`, `odylith doctor`, `odylith version`,
   `intervention-status`, `visible-intervention`, or host compatibility checks
   for this request unless the operator explicitly asked for those diagnostics.
   "Show me what you can do" is the advisory repo capability demo, not proof
   that intervention UX is active in the current chat.
3. Do not paste progress, repair, runtime, status, or failed-fallback chatter
   from stderr. If every show command fails, report only the shortest actionable
   blocker. If there is no repo-local launcher and no `odylith` CLI available,
   say Odylith is not installed in this folder; do not substitute generic host
   work.
4. Print the full stdout directly in your response as-is. Do not summarize,
   diagnose, reformat, or wrap it in a code block. Do not add bullets before
   or after it. Do not run `pwd`, `ls`, `rg`, `git status`, `echo`, or any
   other Bash command after the show command succeeds. End the turn immediately
   after the stdout is visible. The scenario-aware output is already written as
   a trust-first action report with a short mental-model line and should be
   shown verbatim so the operator sees exactly what Odylith said.
5. If the operator names a new project, architecture, research goal, or
   feature after an empty/thin show result, do not refuse because source is
   absent. Run the project-first proposal path instead:
   `./.odylith/bin/odylith greenfield semantic-intent-request --repo-root . --prompt "<their request>"`.
   The active host then authors and challenges the returned source-cited typed
   packet and runs its exact next invocation; Odylith does not parse product
   meaning from the prompt.
   `propose` deterministically verifies the untrusted packet, exact citations,
   typed endpoints, graph completeness, and the full staged
   ProductCreateTransaction without semantic reinterpretation or repair, then
   renders the single visible confirmation view.
   Show the preview directly in chat, including Product story, State object, First
   complete path, actors, systems, assumptions, ambiguities, proof boundary, and one
   clear `## Choose one command` block. **`CONFIRM <hash>`** commits the shown hash-bound
   package; **`EDIT <hash> <corrections>`** accepts corrections as new evidence and rebuilds a new package;
   **`REJECT <hash>`** stops with no writes. Ask one focused question only for material
   uncertainty; otherwise make assumptions visible. Markdown is evidence and a view,
   never product truth. After **`CONFIRM <hash>`**, run
   `greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/pending/<hash>/product-create-transaction.v1.json --transaction-hash <hash> --confirm`.
   Confirmed create only verifies receipt, hash, compiler identity, and repo
   preconditions; applies sealed bytes under rollback guard; validates readback; and
   reports success or environment/IO failure. It does not generate, repair, or parse
   product material after confirmation. Do not ask for a second confirmation, expose
   proposal JSON, search Odylith source for schema, use canned domain scaffolds, dump
   tool internals, or narrate parser/schema retries. Surface only the final transaction,
   created records, or a material blocker.
6. Do not create governance records unless the operator explicitly asks.
   The default posture is advisory — show what's possible and let the operator
   choose.
