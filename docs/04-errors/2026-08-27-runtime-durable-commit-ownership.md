# Runtime Durable Commit Ownership

## Problem

`WorkflowRuntime` previously called `transition_node()` without an explicit transaction contract, while `transition_node()` committed every NodeExecution/Checkpoint transition. That allowed a completed branch to become durable before the Runtime had finished the current execution frontier.

## Fix

`transition_node(..., commit=False)` is now the Runtime contract. NodeExecution state changes, governance trace, and completed-node Checkpoint writes remain in the caller transaction. The outer `WorkflowExecutionService.run()` commits through the final `completed` or `failed` Execution transition.

## Invariant

```text
Runtime node transition
  -> NodeExecution
  -> Trace
  -> Checkpoint
  -> no intermediate commit
  -> Execution completed/failed transition
  -> single durable commit
```

Direct legacy callers retain the default `commit=True` behavior.
