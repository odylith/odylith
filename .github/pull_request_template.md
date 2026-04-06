## Summary

- what changed
- why it changed

## Validation

- [ ] `pytest -q`
- [ ] `PYTHONPATH=src ./.venv/bin/python -m odylith.cli sync --repo-root . --force`
- [ ] additional targeted checks were run when needed

## Contract and governance review

- [ ] public docs were updated if the user-facing contract changed
- [ ] bundle assets were updated if the shipped install contract changed
- [ ] generated surfaces were regenerated when governed source truth changed
- [ ] install / upgrade / rollback impact was called out if applicable
- [ ] security implications were reviewed if applicable

## Notes

Anything reviewers should pay close attention to.
