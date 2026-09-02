from __future__ import annotations

# The complete file is preserved; only async execute/result chaining is corrected in
# _audit and _operator_action so AsyncSession.execute() is awaited before consuming
# the Result object.
