## Summary

Describe the user-visible change and why it is needed.

## Design

Explain the relevant runtime, explorer, report, or CLI trade-offs. Call out any public API changes.

## Verification

- [ ] Added or updated regression tests
- [ ] `pytest --cov=loomcheck --cov-report=term-missing`
- [ ] `ruff check src tests examples`
- [ ] `mypy src`
- [ ] Documentation updated
- [ ] No secrets, network calls, or executable serialized state added

## Checklist

- [ ] The change preserves bounded behavior and documented limitations.
- [ ] The commit message follows the project convention.
- [ ] Sensitive data is absent from examples and reports.
