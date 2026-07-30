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
  const ORIGINAL_PUSH = "__gtmRecetteOriginalPush";

  if (window[GLOBAL_NAME]) {
    return;
  }

  const state = {
    version: 2,
    installedAt: new Date().toISOString(),
    currentActionId: null,
    nextCallIndex: 1,
    layers: {},
    records: [],
    integrity: [],
  };
  const installedLayers = new WeakMap();
  const watchedLayers = new Map();

  function errorText(error) {
    try {
      return String(error && error.message ? error.message : error);
    } catch {
      return "unreadable_error";
    }
  }

  function safeUrl() {
    try {
      return location.href;
    } catch {
      return null;
    }
  }

  function safeTitle() {
    try {
      return document.title;
    } catch {
      return null;
    }
  }

  function safeLength(value) {
    try {
      return value && typeof value.length === "number" ? value.length : null;
    } catch {
      return null;
    }
  }

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
    try {
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
            error: errorText(error),
          };
        }
      }
      return result;
    } finally {
      seen.delete(value);
    }
  }

  function safeSnapshot(value, path = "$") {
    try {
      return typedSnapshot(value, new Map(), path);
    } catch (error) {
      return {
        __gtm_recette_type: "snapshot_failed",
        error: errorText(error),
      };
    }
  }

  function recordIntegrity(layerName, status, detail) {
    try {
      state.integrity.push({
        timestamp: new Date().toISOString(),
        url: safeUrl(),
        layerName,
        status,
        detail,
      });
    } catch {
      // Supplemental instrumentation must never affect the measured site.
    }
  }

  function pushChainContains(push, expected) {
    const visited = new Set();
    let current = push;
    for (let depth = 0; depth < 20 && typeof current === "function"; depth += 1) {
      if (current === expected || current[WRAPPED] === true) {
        return true;
      }
      if (visited.has(current)) {
        return false;
      }
      visited.add(current);
      try {
        current = current[ORIGINAL_PUSH];
      } catch {
        return false;
      }
    }
    return false;
  }

  function uniqueEventIds(args) {
    const output = [];
    for (const item of args) {
      try {
        if (item && typeof item === "object" && item["gtm.uniqueEventId"] !== undefined) {
          output.push(item["gtm.uniqueEventId"]);
        }
      } catch {
        output.push({ __gtm_recette_type: "unreadable" });
      }
    }
    return output;
  }

  function wrapLayer(layerName, layer) {
    if (!Array.isArray(layer)) {
      recordIntegrity(layerName, "invalid_layer", typeof layer);
      return false;
    }

    let currentPush;
    try {
      currentPush = layer.push;
    } catch (error) {
      recordIntegrity(layerName, "push_unreadable", errorText(error));
      return false;
    }
    if (typeof currentPush !== "function") {
      recordIntegrity(layerName, "push_not_callable", typeof currentPush);
      return false;
    }

    const existing = installedLayers.get(layer);
    if (existing) {
      const attached = pushChainContains(currentPush, existing.wrapper);
      state.layers[layerName] = {
        ...state.layers[layerName],
        installed: attached,
        pushReplacedUnverified: !attached,
      };
      if (!attached) {
        recordIntegrity(
          layerName,
          "push_replaced_unverified",
          "The array is unchanged but its outer push function no longer exposes the recorder chain."
        );
      }
      return attached;
    }

    const originalPush = currentPush;
    const preexisting = safeSnapshot(layer, `$preexisting.${layerName}`);

    function recettePush(...args) {
      const callIndex = state.nextCallIndex++;
      const timestamp = new Date().toISOString();
      let performanceNow = null;
      try {
        performanceNow =
          typeof performance !== "undefined" && typeof performance.now === "function"
            ? performance.now()
            : null;
      } catch {
        performanceNow = null;
      }
      const lengthBefore = safeLength(this);
      const argumentSnapshot = safeSnapshot(args, `$call.${callIndex}.arguments`);
      const eventIdsSnapshot = safeSnapshot(
        uniqueEventIds(args),
        `$call.${callIndex}.gtmUniqueEventIds`
      );

      let returnValue;
      let thrown = null;
      try {
        returnValue = Reflect.apply(originalPush, this, args);
      } catch (error) {
        thrown = errorText(error);
        throw error;
      } finally {
        try {
          state.records.push({
            callIndex,
            timestamp,
            performanceNow,
            url: safeUrl(),
            title: safeTitle(),
            layerName,
            actionId: state.currentActionId,
            arguments: argumentSnapshot,
            argumentCount: args.length,
            gtmUniqueEventIds: eventIdsSnapshot,
            arrayLengthBefore: lengthBefore,
            arrayLengthAfter: safeLength(this),
            returnValue: safeSnapshot(
              returnValue,
              `$call.${callIndex}.returnValue`
            ),
            thrown,
          });
        } catch {
          // Never replace the original push outcome with a recorder failure.
        }
      }
      return returnValue;
    }

    Object.defineProperty(recettePush, WRAPPED, {
      value: true,
      enumerable: false,
    });
    Object.defineProperty(recettePush, ORIGINAL_PUSH, {
      value: originalPush,
      enumerable: false,
    });
    try {
      layer.push = recettePush;
    } catch (error) {
      recordIntegrity(layerName, "push_not_replaceable", errorText(error));
      return false;
    }
    installedLayers.set(layer, {
      wrapper: recettePush,
      originalPush,
    });
    state.layers[layerName] = {
      installed: true,
      installedAt: new Date().toISOString(),
      preexistingLength: layer.length,
      preexisting,
      watchedProperty: watchedLayers.has(layerName),
      pushReplacedUnverified: false,
    };
    recordIntegrity(layerName, "installed", `preexisting=${layer.length}`);
    return true;
  }

  function install(layerName = "dataLayer") {
    let layer;
    try {
      layer = window[layerName];
    } catch (error) {
      recordIntegrity(layerName, "layer_unreadable", errorText(error));
      return false;
    }
    if (layer === undefined) {
      layer = [];
      try {
        window[layerName] = layer;
      } catch (error) {
        recordIntegrity(layerName, "layer_not_assignable", errorText(error));
        return false;
      }
    }
    return wrapLayer(layerName, layer);
  }

  function watch(layerName = "dataLayer") {
    if (watchedLayers.has(layerName)) {
      return install(layerName);
    }
    let descriptor;
    try {
      descriptor = Object.getOwnPropertyDescriptor(window, layerName);
    } catch (error) {
      recordIntegrity(layerName, "descriptor_unreadable", errorText(error));
      return install(layerName);
    }
    if (
      descriptor &&
      (!descriptor.configurable || descriptor.get || descriptor.set)
    ) {
      recordIntegrity(
        layerName,
        "property_not_watchable",
        "Existing non-configurable or accessor property was preserved."
      );
      return install(layerName);
    }

    let current = descriptor ? descriptor.value : undefined;
    if (current === undefined) {
      current = [];
    }
    try {
      Object.defineProperty(window, layerName, {
        configurable: true,
        enumerable: descriptor ? descriptor.enumerable : true,
        get() {
          return current;
        },
        set(next) {
          current = next;
          wrapLayer(layerName, next);
        },
      });
    } catch (error) {
      recordIntegrity(layerName, "property_watch_failed", errorText(error));
      return install(layerName);
    }
    watchedLayers.set(layerName, true);
    const attached = wrapLayer(layerName, current);
    if (state.layers[layerName]) {
      state.layers[layerName].watchedProperty = true;
    }
    return attached;
  }

  function checkIntegrity(layerName = "dataLayer") {
    let layer;
    let push;
    try {
      layer = window[layerName];
      push = layer && layer.push;
    } catch {
      layer = null;
      push = null;
    }
    const installed = Array.isArray(layer) ? installedLayers.get(layer) : null;
    const recorderAttached = Boolean(
      installed && typeof push === "function" && pushChainContains(push, installed.wrapper)
    );
    const result = {
      layerName,
      timestamp: new Date().toISOString(),
      url: safeUrl(),
      isArray: Array.isArray(layer),
      pushCallable: typeof push === "function",
      recorderAttached,
      pushReplacedUnverified: Boolean(installed && !recorderAttached),
      watchedProperty: watchedLayers.has(layerName),
      length: Array.isArray(layer) ? safeLength(layer) : null,
    };
    if (!result.recorderAttached) {
      recordIntegrity(
        layerName,
        result.pushReplacedUnverified
          ? "push_replaced_unverified"
          : "recorder_detached",
        JSON.stringify(result)
      );
    }
    return result;
  }

  const api = {
    version: 2,
    install,
    watch,
    markAction(actionId) {
      state.currentActionId = actionId === null ? null : String(actionId);
      return state.currentActionId;
    },
    clearAction() {
      state.currentActionId = null;
    },
    checkIntegrity,
    snapshot() {
      return safeSnapshot(state);
    },
    recordsSince(callIndex = 0) {
      return safeSnapshot(
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

  watch("dataLayer");
})();
