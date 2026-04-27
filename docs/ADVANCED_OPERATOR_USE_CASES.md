# Advanced Operator Use Cases

Normal coding-agent use should not require these commands.

Use them when you are inspecting grounding behavior, checking explicit impact
or topology, or forcing a local refresh path while debugging Odylith itself.

```bash
odylith context-engine --repo-root . bootstrap-session --working-tree --working-tree-scope session --session-id agent-main
odylith context-engine --repo-root . impact <paths...>
odylith context-engine --repo-root . architecture <paths...>
odylith sync --repo-root . --force
```

## What These Commands Are For

- `bootstrap-session`: inspect fresh session grounding directly.
- `impact`: inspect likely impact and supporting evidence for explicit paths.
- `architecture`: inspect topology, boundaries, and architectural evidence for
  explicit paths.
- `sync --force`: force a full local surface refresh when you are debugging
  generated state or renderer output.

For deeper engine detail, see
[Context Engine](CONTEXT_ENGINE.md).
