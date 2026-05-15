# Odylith Show Me

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
example application files such as HTML/CSS/JS demos, toy apps, sample robots, or
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
   or after it. The scenario-aware output is already written as a trust-first action report with a short mental-model line and should be shown verbatim so the operator sees exactly what Odylith said.
5. If the operator names a new project, architecture, research goal, or
   feature after an empty/thin show result, do not refuse because source is
   absent. Run the project-first proposal path instead:
   `./.odylith/bin/odylith greenfield propose --repo-root . --prompt "<their request>"`.
   Treat that output as a no-write Product Intent request. Write the short
   Product Intent Confirmation in chat from live reasoning so the operator sees
   the interpreted product story, actors, systems, assumptions, ambiguities,
   and confirm/edit/reject gate. After the operator confirms the same
   interpretation, write that same visible confirmation to
   `.odylith/runtime/greenfield/confirmed-intent.md`, then run the confirmed
   create path from the same confirmation:
   `greenfield create --repo-root . --prompt "<their request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`.
   Odylith builds the apply-ready proposal from the accepted narrative,
   validates it, runs Tribunal, writes records, and refreshes surfaces; do not
   show JSON as a second approval step and do not search Odylith source,
   `.odylith`, bundle files, or local examples for schema.
   Do not ask the operator to inspect proposal JSON or confirm a second time unless they explicitly request a review artifact.
   Do not hand-author or repair proposal JSON, use canned domain scaffolds, dump
   tool internals, or write code before the product gates are accepted. When the CLI
   returns proposal stdout directly before confirmation, do not hide the
   confirmation behind collapsed tool output. After confirmation, surface only
   created records or validation/Tribunal blockers.
6. Do not create governance records unless the operator explicitly asks.
   The default posture is advisory — show what's possible and let the operator
   choose.
