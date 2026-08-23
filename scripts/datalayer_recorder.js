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
  const SNAPSHOT_LIMITS = Object.freeze({
    maxDepth: 64,
    maxNodes: 12000,
    maxElapsedMs: 16,
  });

  if (window[GLOBAL_NAME]) {
    return;
  }

  const state = {
    version: 3,
    runId:
      typeof window.__gtmRecetteRunId === "string" && window.__gtmRecetteRunId.trim()
        ? window.__gtmRecetteRunId.trim()
        : null,
    installedAt: new Date().toISOString(),
    installedAtDocumentStart:
      window.__gtmRecetteInstalledAtDocumentStart === true,
    documentId: null,
    frameId: null,
    currentActionId: null,
    nextCallIndex: 1,
    acknowledgedThrough: 0,
    layers: {},
    records: [],
    integrity: [],
    disposed: false,
  };
  const installedLayers = new WeakMap();
  const watchedLayers = new Map();
  const layerBindings = new Map();

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

  function snapshotClock() {
    try {
      return typeof performance !== "undefined" && typeof performance.now === "function"
        ? performance.now()
        : Date.now();
    } catch {
      return Date.now();
    }
  }

  function truncatedSnapshot(context, reason, path) {
    if (!context.truncated) {
      context.truncated = true;
      context.truncationReason = reason;
      context.truncationPath = path;
    }
    return {
      __gtm_recette_type: "snapshot_truncated",
      reason: context.truncationReason,
      path: context.truncationPath,
      nodeCount: context.nodes,
    };
  }

  function snapshotBudget(context, path, depth) {
    if (context.truncated) {
      return truncatedSnapshot(context, context.truncationReason, context.truncationPath);
    }
    if (depth > context.limits.maxDepth) {
      return truncatedSnapshot(context, "max_depth", path);
    }
    context.nodes += 1;
    if (context.nodes > context.limits.maxNodes) {
      return truncatedSnapshot(context, "max_nodes", path);
    }
    if (
      context.nodes % 64 === 0 &&
      snapshotClock() - context.startedAt > context.limits.maxElapsedMs
    ) {
      return truncatedSnapshot(context, "max_elapsed_ms", path);
    }
    return null;
  }

  function typedSnapshot(value, context, path = "$", depth = 0) {
    const budgetResult = snapshotBudget(context, path, depth);
    if (budgetResult) {
      return budgetResult;
    }
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

    if (context.ancestors.has(value)) {
      return {
        __gtm_recette_type: "circular_reference",
        reference: context.visited.get(value),
      };
    }
    if (context.visited.has(value)) {
      return {
        __gtm_recette_type: "shared_reference",
        reference: context.visited.get(value),
      };
    }
    context.visited.set(value, path);
    context.ancestors.add(value);
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
        const result = [];
        for (let index = 0; index < value.length; index += 1) {
          try {
            result.push(
              typedSnapshot(value[index], context, `${path}[${index}]`, depth + 1)
            );
          } catch (error) {
            result.push({
              __gtm_recette_type: "unreadable",
              error: errorText(error),
            });
          }
          if (context.truncated) {
            break;
          }
        }
        return result;
      }

      const result = {};
      for (const key in value) {
        if (!Object.prototype.hasOwnProperty.call(value, key)) {
          continue;
        }
        try {
          result[key] = typedSnapshot(value[key], context, `${path}.${key}`, depth + 1);
        } catch (error) {
          result[key] = {
            __gtm_recette_type: "unreadable",
            error: errorText(error),
          };
        }
        if (context.truncated) {
          break;
        }
      }
      return result;
    } finally {
      context.ancestors.delete(value);
    }
  }

  function safeSnapshot(value, path = "$") {
    try {
      const context = {
        visited: new Map(),
        ancestors: new Set(),
        nodes: 0,
        startedAt: snapshotClock(),
        truncated: false,
        truncationReason: null,
        truncationPath: null,
        limits: SNAPSHOT_LIMITS,
      };
      return typedSnapshot(value, context, path, 0);
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
            documentId: state.documentId,
            frameId: state.frameId,
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
    layerBindings.set(layerName, {
      layer,
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
    watchedLayers.set(layerName, {
      originalDescriptor: descriptor || null,
    });
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

  function uninstall(layerName = "dataLayer") {
    const binding = layerBindings.get(layerName);
    let current;
    try {
      current = window[layerName];
    } catch (error) {
      recordIntegrity(layerName, "uninstall_unreadable", errorText(error));
      return false;
    }
    if (binding && current === binding.layer) {
      let currentPush;
      try {
        currentPush = current.push;
      } catch {
        currentPush = null;
      }
      if (currentPush === binding.wrapper) {
        try {
          current.push = binding.originalPush;
        } catch (error) {
          recordIntegrity(layerName, "uninstall_push_failed", errorText(error));
          return false;
        }
      } else if (pushChainContains(currentPush, binding.wrapper)) {
        recordIntegrity(
          layerName,
          "uninstall_nested_wrapper",
          "A later wrapper contains the recorder; automatic removal would alter site code."
        );
        return false;
      }
    }
    const watched = watchedLayers.get(layerName);
    if (watched) {
      try {
        const original = watched.originalDescriptor;
        if (original) {
          Object.defineProperty(window, layerName, {
            ...original,
            value: current,
          });
        } else {
          Object.defineProperty(window, layerName, {
            configurable: true,
            enumerable: true,
            writable: true,
            value: current,
          });
        }
      } catch (error) {
        recordIntegrity(layerName, "uninstall_property_failed", errorText(error));
        return false;
      }
    }
    layerBindings.delete(layerName);
    watchedLayers.delete(layerName);
    delete state.layers[layerName];
    return true;
  }

  const api = {
    version: 3,
    install,
    watch,
    uninstall,
    beginRun(runId, options = {}) {
      const normalized = String(runId || "").trim();
      if (!normalized) {
        throw new TypeError("runId must be a non-empty string");
      }
      const changingRun = state.runId !== null && state.runId !== normalized;
      if (changingRun && state.records.length > 0 && options.reset !== true) {
        throw new Error(
          "Recorder contains another run. Export it or call beginRun(runId, {reset: true})."
        );
      }
      if (changingRun && options.reset === true) {
        state.records = [];
        state.integrity = [];
        state.nextCallIndex = 1;
        state.acknowledgedThrough = 0;
        state.currentActionId = null;
        state.installedAt = new Date().toISOString();
      }
      state.runId = normalized;
      if (Object.prototype.hasOwnProperty.call(options, "installedAtDocumentStart")) {
        state.installedAtDocumentStart = options.installedAtDocumentStart === true;
      }
      if (Object.prototype.hasOwnProperty.call(options, "documentId")) {
        state.documentId = options.documentId === null ? null : String(options.documentId);
      }
      if (Object.prototype.hasOwnProperty.call(options, "frameId")) {
        state.frameId = options.frameId === null ? null : String(options.frameId);
      }
      return state.runId;
    },
    markAction(actionId) {
      state.currentActionId = actionId === null ? null : String(actionId);
      return state.currentActionId;
    },
    clearAction() {
      state.currentActionId = null;
    },
    checkIntegrity,
    snapshot() {
      return {
        version: state.version,
        runId: state.runId,
        disposed: state.disposed,
        installedAt: state.installedAt,
        installedAtDocumentStart: state.installedAtDocumentStart,
        captureMode: "call_time",
        complete: checkIntegrity("dataLayer").recorderAttached,
        document_id: state.documentId,
        frame_id: state.frameId,
        currentActionId: state.currentActionId,
        nextCallIndex: state.nextCallIndex,
        acknowledgedThrough: state.acknowledgedThrough,
        earliestRetainedCallIndex:
          state.records.length > 0 ? state.records[0].callIndex : null,
        layers: safeSnapshot(state.layers, "$.layers"),
        records: state.records.map((record, index) =>
          safeSnapshot(record, `$.records[${index}]`)
        ),
        integrity: state.integrity.map((record, index) =>
          safeSnapshot(record, `$.integrity[${index}]`)
        ),
      };
    },
    recordsSince(callIndex = 0) {
      return state.records
        .filter((record) => record.callIndex > Number(callIndex || 0))
        .map((record, index) =>
          safeSnapshot(record, `$.recordsSince[${index}]`)
        );
    },
    captureSince(callIndex = 0) {
      const cursor = Number(callIndex || 0);
      const integrity = checkIntegrity("dataLayer");
      return {
        version: state.version,
        runId: state.runId,
        captureMode: "call_time",
        installedAtDocumentStart: state.installedAtDocumentStart,
        complete: integrity.recorderAttached,
        document_id: state.documentId,
        frame_id: state.frameId,
        cursor_start: cursor,
        cursor_end: state.nextCallIndex - 1,
        records: api.recordsSince(cursor),
        integrity: [integrity],
      };
    },
    acknowledgeThrough(callIndex) {
      const numeric = Number(callIndex);
      if (!Number.isInteger(numeric) || numeric < 0) {
        throw new TypeError("callIndex must be a non-negative integer");
      }
      const latestRecorded = state.nextCallIndex - 1;
      if (numeric > latestRecorded) {
        throw new RangeError("callIndex cannot exceed the latest recorded call");
      }
      const before = state.records.length;
      state.records = state.records.filter((record) => record.callIndex > numeric);
      state.acknowledgedThrough = Math.max(state.acknowledgedThrough, numeric);
      return {
        acknowledgedThrough: state.acknowledgedThrough,
        removed: before - state.records.length,
        remaining: state.records.length,
        nextCallIndex: state.nextCallIndex,
      };
    },
    dispose() {
      if (state.disposed) {
        return {disposed: true, alreadyDisposed: true, failures: []};
      }
      const names = new Set([...layerBindings.keys(), ...watchedLayers.keys()]);
      const failures = [...names].filter((layerName) => !uninstall(layerName));
      if (failures.length > 0) {
        return {disposed: false, failures};
      }
      state.records = [];
      state.integrity = [];
      state.currentActionId = null;
      state.runId = null;
      state.disposed = true;
      return {disposed: true, alreadyDisposed: false, failures: []};
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
