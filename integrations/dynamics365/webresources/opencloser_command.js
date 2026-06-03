(function (global) {
  "use strict";

  var CONFIG_SCHEMA = {
    apiBaseUrl: "oc_OpenCloserApiBaseUrl",
    triggerMode: "oc_OpenCloserTriggerMode",
    powerAutomateTriggerUrl: "oc_OpenCloserPowerAutomateTriggerUrl",
    defaultRunMode: "oc_OpenCloserDefaultRunMode",
    testModeEnabled: "oc_OpenCloserTestModeEnabled",
    maxCampaignBatchSize: "oc_OpenCloserMaxCampaignBatchSize",
    allowedCampaignCodes: "oc_OpenCloserAllowedCampaignCodes"
  };

  var ACTIONS = {
    ai_call_lead: {
      entityName: "lead",
      endpoint: function (baseUrl, recordId) {
        return trimTrailingSlash(baseUrl) + "/v1/crm/dataverse/leads/" + recordId + "/ai-call";
      },
      confirmTitle: "AI Call Lead",
      confirmText: "Start an openCloser AI call attempt for this Lead?"
    },
    run_campaign: {
      entityName: "campaign",
      endpoint: function (baseUrl, recordId) {
        return trimTrailingSlash(baseUrl) + "/v1/crm/dataverse/campaigns/" + recordId + "/run";
      },
      confirmTitle: "Run openCloser Campaign",
      confirmText: "Start an openCloser campaign run for eligible Leads in this Campaign?"
    }
  };

  function trimTrailingSlash(value) {
    return String(value || "").replace(/\/+$/, "");
  }

  function stripBraces(value) {
    return String(value || "").replace(/[{}]/g, "").toLowerCase();
  }

  function parseBool(value) {
    return String(value || "").toLowerCase() === "true";
  }

  function parsePositiveInt(value, fallback) {
    var parsed = parseInt(value, 10);
    if (Number.isNaN(parsed) || parsed < 1) {
      return fallback;
    }
    return parsed;
  }

  function getFormContext(primaryControl) {
    if (!primaryControl || !primaryControl.data || !primaryControl.data.entity) {
      throw new Error("PrimaryControl form context was not available.");
    }
    return primaryControl;
  }

  function getRecordContext(primaryControl, expectedEntityName) {
    var formContext = getFormContext(primaryControl);
    var entity = formContext.data.entity;
    var entityName = entity.getEntityName();

    if (entityName !== expectedEntityName) {
      throw new Error("This command is configured for " + expectedEntityName + " but ran on " + entityName + ".");
    }

    var recordId = stripBraces(entity.getId());
    if (!recordId) {
      throw new Error("Save the record before triggering openCloser.");
    }

    return {
      entityName: entityName,
      id: recordId
    };
  }

  function getCrmContext() {
    var context = Xrm.Utility.getGlobalContext();
    return {
      clientUrl: context.getClientUrl(),
      organizationId: stripBraces(context.organizationSettings.organizationId),
      userId: stripBraces(context.userSettings.userId)
    };
  }

  async function readEnvironmentVariable(schemaName) {
    var query = [
      "?$select=schemaname,defaultvalue",
      "&$expand=environmentvariabledefinition_environmentvariablevalue($select=value)",
      "&$filter=schemaname eq '" + schemaName.replace(/'/g, "''") + "'"
    ].join("");

    var result = await Xrm.WebApi.retrieveMultipleRecords("environmentvariabledefinition", query);
    if (!result.entities || result.entities.length === 0) {
      return "";
    }

    var definition = result.entities[0];
    var values = definition.environmentvariabledefinition_environmentvariablevalue || [];
    if (values.length > 0 && values[0].value) {
      return values[0].value;
    }

    return definition.defaultvalue || "";
  }

  async function loadConfig() {
    var values = {};
    var keys = Object.keys(CONFIG_SCHEMA);

    for (var i = 0; i < keys.length; i += 1) {
      var key = keys[i];
      values[key] = await readEnvironmentVariable(CONFIG_SCHEMA[key]);
    }

    return {
      apiBaseUrl: values.apiBaseUrl,
      triggerMode: values.triggerMode || "direct-api",
      powerAutomateTriggerUrl: values.powerAutomateTriggerUrl,
      defaultRunMode: values.defaultRunMode || "dry_run",
      testModeEnabled: parseBool(values.testModeEnabled),
      maxCampaignBatchSize: parsePositiveInt(values.maxCampaignBatchSize, 10),
      allowedCampaignCodes: values.allowedCampaignCodes || ""
    };
  }

  function buildPayload(actionName, recordContext, config) {
    return {
      source: "dynamics365-command-bar",
      action: actionName,
      record: recordContext,
      crm: getCrmContext(),
      run: {
        mode: config.defaultRunMode,
        testMode: config.testModeEnabled,
        maxCampaignBatchSize: config.maxCampaignBatchSize,
        assignmentTag: null,
        requestedAt: new Date().toISOString()
      }
    };
  }

  async function confirmAction(action) {
    var response = await Xrm.Navigation.openConfirmDialog(
      {
        title: action.confirmTitle,
        text: action.confirmText,
        confirmButtonLabel: "Start",
        cancelButtonLabel: "Cancel"
      },
      {
        height: 220,
        width: 480
      }
    );

    return response.confirmed === true;
  }

  async function postJson(url, payload) {
    var response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    var responseText = await response.text();
    var responseBody = {};

    if (responseText) {
      try {
        responseBody = JSON.parse(responseText);
      } catch (error) {
        responseBody = { message: responseText };
      }
    }

    if (!response.ok) {
      throw new Error(responseBody.message || ("openCloser trigger failed with HTTP " + response.status + "."));
    }

    return responseBody;
  }

  function getTriggerUrl(actionName, action, recordContext, config) {
    if (config.triggerMode === "power-automate") {
      if (!config.powerAutomateTriggerUrl) {
        throw new Error("Power Automate trigger mode is enabled, but no trigger URL is configured.");
      }
      return config.powerAutomateTriggerUrl;
    }

    if (config.triggerMode !== "direct-api") {
      throw new Error("Unsupported openCloser trigger mode: " + config.triggerMode + ".");
    }

    if (!config.apiBaseUrl) {
      throw new Error("openCloser API base URL is not configured.");
    }

    return action.endpoint(config.apiBaseUrl, recordContext.id);
  }

  async function runCommand(actionName, primaryControl) {
    var action = ACTIONS[actionName];

    try {
      var recordContext = getRecordContext(primaryControl, action.entityName);
      var confirmed = await confirmAction(action);
      if (!confirmed) {
        return;
      }

      Xrm.Utility.showProgressIndicator("Starting openCloser...");

      var config = await loadConfig();
      var payload = buildPayload(actionName, recordContext, config);
      var triggerUrl = getTriggerUrl(actionName, action, recordContext, config);
      var response = await postJson(triggerUrl, payload);

      Xrm.Utility.closeProgressIndicator();
      await Xrm.Navigation.openAlertDialog({
        title: "openCloser",
        text: response.message || "openCloser run accepted."
      });
    } catch (error) {
      Xrm.Utility.closeProgressIndicator();
      await Xrm.Navigation.openAlertDialog({
        title: "openCloser",
        text: error.message || "openCloser trigger failed."
      });
    }
  }

  global.OpenCloser = global.OpenCloser || {};
  global.OpenCloser.Commands = {
    aiCallLead: function (primaryControl) {
      return runCommand("ai_call_lead", primaryControl);
    },
    runCampaign: function (primaryControl) {
      return runCommand("run_campaign", primaryControl);
    }
  };
})(window);
