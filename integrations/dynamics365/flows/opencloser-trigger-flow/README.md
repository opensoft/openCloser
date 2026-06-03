# openCloser Trigger Flow

Placeholder for the Power Automate flow that forwards Dynamics command-bar
requests to openCloser.

Expected flow behavior:

1. Accept the JSON payload documented in `docs/api-contract.md`.
2. Validate required fields: `action`, `record.entityName`, `record.id`, and
   `crm.clientUrl`.
3. Call the configured openCloser runtime endpoint.
4. Return the openCloser status and user-safe message.

Do not put call business logic in the flow.

