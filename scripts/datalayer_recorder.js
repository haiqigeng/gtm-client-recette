/*
 * Supplemental GTM recette dataLayer journal.
 *
 * Install with Playwright browserContext.addInitScript() before opening the
 * tested website. Tag Assistant remains authoritative for GTM Preview evidence.
 * This recorder preserves browser-side call chronology and must be labelled
 * browser_interception in normalized evidence.
 */
(() => {
  "use strict";

  const GLOBAL_NAME = "__gtmRecetteJournal";
  const WRAPPED = Symbol.for("gtm-recette.dataLayer-wrapped");

  if (window[GLOBAL_NAME] && window[GLOBAL_NAME].version === 1) {
    return;
  }

  const state = {
    version: 1,
    installedAt: new Date().toISOString(),
    currentActionId: null,
    nextCallIndex: 1,
    layers: {},
    records: [],
    integrity: [],
  };

  function typedSnapshot(value, seen = new Map(), path = "$") {
    if (value === undefined) {
      return { __gtm_recette_type: "undefined" };
    }
    if (value === null) {
      return null;
    }

    const valueType = typeof value;
    if (valueType === "number") {
      if (Number.isNaN(value)) {
        return { __gtm_recette_type: "number", value: "NaN" };
      }
      if (!Number.isFinite(value)) {
        return {
          __gtm_recette_type: "number",
          value: value > 0 ? "Infinity" : "-Infinity",
        };
      }
      return value;
    }
    if (valueType === "bigint") {
      return { __gtm_recette_type: "bigint", value: value.toString() };
    }
    if (valueType === "function") {
      return {
        __gtm_recette_type: "function",
        name: value.name || null,
      };
    }
    if (valueType === "symbol") {
      return {
        __gtm_recette_type: "symbol",
        description: value.description || null,
      };
    }
    if (valueType !== "object") {
      return value;
    }

    if (seen.has(value)) {
      return {
        __gtm_recette_type: "circular_reference",
        reference: seen.get(value),
      };
    }
    seen.set(value, path);

    if (value instanceof Date) {
      return {
        __gtm_recette_type: "date",
        value: Number.isNaN(value.getTime()) ? "Invalid Date" : value.toISOString(),
      };
    }
    if (value instanceof RegExp) {
      return {
        __gtm_recette_type: "regexp",
        source: value.source,
        flags: value.flags,
      };
    }
    if (Array.isArray(value)) {
      return value.map((item, index) =>
        typedSnapshot(item, seen, `${path}[${index}]`)
      );
    }

    const result = {};
    for (const key of Object.keys(value)) {
      try {
        result[key] = typedSnapshot(value[key], seen, `${path}.${key}`);
      } catch (error) {
        result[key] = {
          __gtm_recette_type: "unreadable",
          error: String(error && error.message ? error.message : error),
        };
      }
    }
    return result;
  }

  function recordIntegrity(layerName, status, detail) {
    state.integrity.push({
      timestamp: new Date().toISOString(),
      url: location.href,
      layerName,
      status,
      detail,
    });
  }

  function install(layerName = "dataLayer") {
    let layer = window[layerName];
    if (layer === undefined) {
      layer = [];
      window[layerName] = layer;
    }
    if (!Array.isArray(layer)) {
      recordIntegrity(layerName, "invalid_layer", typeof layer);
      return false;
    }
    if (typeof layer.push !== "function") {
      recordIntegrity(layerName, "push_not_callable", typeof layer.push);
      return false;
    }
    if (layer.push[WRAPPED]) {
      state.layers[layerName] = {
        installed: true,
        installedAt: state.layers[layerName]?.installedAt || new Date().toISOString(),
        preexistingLength: state.layers[layerName]?.preexistingLength || layer.length,
      };
      return true;
    }

    const originalPush = layer.push;
    const preexisting = typedSnapshot(Array.from(layer));

    function recettePush(...args) {
      const callIndex = state.nextCallIndex++;
      const timestamp = new Date().toISOString();
      const performanceNow =
        typeof performance !== "undefined" && typeof performance.now === "function"
          ? performance.now()
          : null;
      const lengthBefore = this && typeof this.length === "number" ? this.length : null;
      const argumentSnapshot = typedSnapshot(args);
      const uniqueEventIds = args
        .map((item) =>
          item && typeof item === "object" ? item["gtm.uniqueEventId"] : undefined
        )
        .filter((item) => item !== undefined);

      let returnValue;
      let thrown = null;
      try {
        returnValue = Reflect.apply(originalPush, this, args);
      } catch (error) {
        thrown = String(error && error.message ? error.message : error);
        throw error;
      } finally {
        state.records.push({
          callIndex,
          timestamp,
          performanceNow,
          url: location.href,
          title: document.title,
          layerName,
          actionId: state.currentActionId,
          arguments: argumentSnapshot,
          argumentCount: args.length,
          gtmUniqueEventIds: typedSnapshot(uniqueEventIds),
          arrayLengthBefore: lengthBefore,
          arrayLengthAfter:
            this && typeof this.length === "number" ? this.length : null,
          returnValue: typedSnapshot(returnValue),
          thrown,
        });
      }
      return returnValue;
    }

    Object.defineProperty(recettePush, WRAPPED, {
      value: true,
      enumerable: false,
    });
    Object.defineProperty(recettePush, "__gtmRecetteOriginalPush", {
      value: originalPush,
      enumerable: false,
    });
    layer.push = recettePush;
    state.layers[layerName] = {
      installed: true,
      installedAt: new Date().toISOString(),
      preexistingLength: layer.length,
      preexisting,
    };
    recordIntegrity(layerName, "installed", `preexisting=${layer.length}`);
    return true;
  }

  function checkIntegrity(layerName = "dataLayer") {
    const layer = window[layerName];
    const result = {
      layerName,
      timestamp: new Date().toISOString(),
      url: location.href,
      isArray: Array.isArray(layer),
      pushCallable: Boolean(layer && typeof layer.push === "function"),
      recorderAttached: Boolean(layer && layer.push && layer.push[WRAPPED]),
      length: Array.isArray(layer) ? layer.length : null,
    };
    if (!result.recorderAttached) {
      recordIntegrity(layerName, "recorder_detached", JSON.stringify(result));
    }
    return result;
  }

  const api = {
    version: 1,
    install,
    markAction(actionId) {
      state.currentActionId = actionId === null ? null : String(actionId);
      return state.currentActionId;
    },
    clearAction() {
      state.currentActionId = null;
    },
    checkIntegrity,
    snapshot() {
      return typedSnapshot(state);
    },
    recordsSince(callIndex = 0) {
      return typedSnapshot(
        state.records.filter((record) => record.callIndex > Number(callIndex || 0))
      );
    },
  };

  Object.defineProperty(window, GLOBAL_NAME, {
    value: api,
    configurable: false,
    enumerable: false,
    writable: false,
  });

  install("dataLayer");
})();
