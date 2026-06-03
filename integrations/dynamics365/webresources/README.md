# Web Resources

`opencloser_command.js` is the command bar handler library for Dynamics model-
driven apps.

Register these functions on command bar buttons:

| Table | Button label | Function | Parameter |
|---|---|---|---|
| Lead | `AI Call Lead` | `OpenCloser.Commands.aiCallLead` | `PrimaryControl` |
| Campaign | `Run openCloser Campaign` | `OpenCloser.Commands.runCampaign` | `PrimaryControl` |

The web resource only collects record context, confirms user intent, reads
Dataverse environment variables, and triggers openCloser. The openCloser runtime
performs eligibility, DNC handling, call execution, and CRM write-back.

