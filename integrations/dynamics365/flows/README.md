# Power Automate Flows

This directory is reserved for solution-owned cloud flows.

For the first installable Dynamics solution, prefer a small trigger flow when
browser-to-openCloser authentication or CORS is not ready:

```text
Command bar JavaScript
  -> Power Automate HTTP trigger
  -> openCloser runtime API
  -> Dataverse write-back adapter
```

The flow should not implement eligibility, DNC logic, persona logic, fixture
selection, call execution, or write-back idempotency. It only forwards a signed
request and returns a user-safe response to the command bar handler.

