# Odylith Show Me

Use this skill when the operator says "show me what you can do", "what can
Odylith do", "what can you do for this repo", or any similar first-time
exploration request. Works identically on Claude Code and Codex.

1. Run `./.odylith/bin/odylith show --repo-root .` and capture the stdout.
2. Print the full output directly in your response as-is. Do not summarize,
   reformat, or wrap it in a code block. The output is already written in
   plain English and should be shown verbatim so the operator sees exactly
   what Odylith said.
3. If the operator wants to create everything at once, run
   `./.odylith/bin/odylith show --repo-root . --apply`.
4. Do not create governance records unless the operator explicitly asks.
   The default posture is advisory — show what's possible and let the operator
   choose.
