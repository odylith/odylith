# casebook-bug-investigation

Use when investigating an existing bug through local repo truth, Odylith packets, and linked runtime evidence.

## Canonical Commands

```bash
odylith context-engine --repo-root . impact <paths...>
odylith context-engine --repo-root . architecture <paths...>
odylith sync --repo-root . --check-only --check-clean
```

## Rules

- Keep investigation grounded in local repo truth and linked historical evidence.
- Prefer bounded packet assistance over broad repo scans only after the evidence cone is grounded.
