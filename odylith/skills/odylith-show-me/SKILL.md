# Odylith Show Me

Use this skill when the operator says "show me what you can do", "what can
Odylith do", "what can you do for this repo", or any similar first-time
exploration request. Works identically on Claude Code and Codex.

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
   blocker.
4. Print the full stdout directly in your response as-is. Do not summarize,
   reformat, or wrap it in a code block. The output is already written in
   plain English and should be shown verbatim so the operator sees exactly
   what Odylith said.
5. If the operator wants to create everything at once, run the same selected
   command with `--apply`, for example
   `./.odylith/bin/odylith show --repo-root . --apply`.
6. Do not create governance records unless the operator explicitly asks.
   The default posture is advisory — show what's possible and let the operator
   choose.
