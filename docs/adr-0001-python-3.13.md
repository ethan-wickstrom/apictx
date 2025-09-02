# ADR 0001: Require Python 3.13

## Context

The project initially targeted Python 3.12. Modern functional constructs and
standard library improvements in Python 3.13 simplify the pipeline and enable
slot-based dataclasses.

## Decision

Pin the minimum supported version to Python 3.13 and update build tooling and
code accordingly. Adopt `itertools.chain` and other functional helpers to reduce
mutable state.

## Consequences

- Developers must use Python 3.13.
- Older Python releases are unsupported.
- Functional helpers improve readability and maintainability.

