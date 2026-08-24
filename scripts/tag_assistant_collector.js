(async (spec) => {
  "use strict";

  const contract = spec && typeof spec === "object" ? spec : {};
  const cursor = contract.preview_cursor || {};
  const cursorStart = Number.isFinite(Number(cursor.index)) ? Number(cursor.index) : 0;
  const timeoutMs = Math.max(500, Math.min(Number(contract.timeout_ms) || 5000, 5000));
  const deadline = Date.now() + timeoutMs;
  const wantedPanels = new Set(contract.preview_panels || ["API Call", "Tags"]);
  const sourceNames = new Set(
    ((contract.source_anchor && contract.source_anchor.event_names) || [])
      .map((value) => String(value).trim().toLowerCase())
      .filter(Boolean),
  );
  const deliveryNames = new Set(
    (contract.delivery_event_names || [])
      .map((value) => String(value).trim().toLowerCase())
      .filter(Boolean),
  );
  const declaredTags = (contract.tag_ids || []).map(String).filter(Boolean);
  const tagScopes = (contract.tag_scope || [])
    .map((value) => String(value).trim().toLowerCase())
    .filter(Boolean);
  const stateOnly = contract.source_anchor?.mode === "state_fields";
  const fieldLeaves = ((contract.source_anchor && contract.source_anchor.field_paths) || [])
    .map((value) => String(value).split(".").pop().replace(/\[\]/g, "").toLowerCase())
    .filter(Boolean);
  const technicalName = /^(?:gtm\.|message$|trigger\s*group$|container\s*loaded$|dom\s*ready$|window\s*loaded$|consent)/i;
  let fallbackUsed = false;

  const visible = (node) => {
    const style = getComputedStyle(node);
    return style.display !== "none" && style.visibility !== "hidden" && node.getClientRects().length > 0;
  };
  const compact = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const tagCategory = (label) => {
    if (/\bga4\b|google analytics|google tag/i.test(label)) return "GA4";
    if (/google ads|adwords|conversion linker/i.test(label)) return "Google Ads";
    return "Other";
  };
  const tagInScope = (label) => {
    if (!tagScopes.length) return true;
    const text = String(label).toLowerCase();
    return tagScopes.some((scope) => {
      if (scope === "ga4" || scope === "google analytics") {
        return /\bga4\b|google analytics|google tag/i.test(text);
      }
      if (scope === "google ads" || scope === "googleads" || scope === "adwords") {
        return /google ads|adwords|conversion linker/i.test(text);
      }
      return text.includes(scope);
    });
  };

  const tokenize = (text) => {
    const tokens = [];
    let position = 0;
    const push = (type, value) => tokens.push({ type, value });
    while (position < text.length) {
      const character = text[position];
      if (/\s/.test(character)) { position += 1; continue; }
      if ("{}[]:,()+".includes(character)) { push(character, character); position += 1; continue; }
      if (character === '"' || character === "'" || character === "`") {
        const quote = character;
        let value = "";
        position += 1;
        let closed = false;
        while (position < text.length) {
          const current = text[position++];
          if (current === quote) { closed = true; break; }
          if (current !== "\\") { value += current; continue; }
          if (position >= text.length) break;
          const escaped = text[position++];
          const escapes = { n: "\n", r: "\r", t: "\t", b: "\b", f: "\f", v: "\v" };
          if (escaped === "u" && /^[0-9a-fA-F]{4}$/.test(text.slice(position, position + 4))) {
            value += String.fromCharCode(parseInt(text.slice(position, position + 4), 16));
            position += 4;
          } else {
            value += Object.prototype.hasOwnProperty.call(escapes, escaped) ? escapes[escaped] : escaped;
          }
        }
        if (!closed) throw new Error("Unterminated string");
        push("value", value);
        continue;
      }
      const number = text.slice(position).match(/^-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/i);
      if (number) { push("value", Number(number[0])); position += number[0].length; continue; }
      const identifier = text.slice(position).match(/^[A-Za-z_$][\w$.-]*/);
      if (identifier) {
        const word = identifier[0];
        const literals = { true: true, false: false, null: null, undefined: null, NaN: null };
        push("value", Object.prototype.hasOwnProperty.call(literals, word) ? literals[word] : word);
        position += word.length;
        continue;
      }
      throw new Error(`Unsupported token at ${position}`);
    }
    return tokens;
  };

  const parseLiteralList = (text) => {
    const tokens = tokenize(text);
    let position = 0;
    const peek = () => tokens[position];
    const take = (type) => {
      const token = tokens[position];
      if (!token || token.type !== type) throw new Error(`Expected ${type}`);
      position += 1;
      return token.value;
    };
    let parseValue;
    const parseAtom = () => {
      const token = peek();
      if (!token) throw new Error("Missing value");
      if (token.type === "value") { position += 1; return token.value; }
      if (token.type === "{") {
        position += 1;
        const output = {};
        while (peek() && peek().type !== "}") {
          const key = String(take("value"));
          take(":");
          output[key] = parseValue();
          if (peek()?.type === ",") position += 1;
          else break;
        }
        take("}");
        return output;
      }
      if (token.type === "[") {
        position += 1;
        const output = [];
        while (peek() && peek().type !== "]") {
          output.push(parseValue());
          if (peek()?.type === ",") position += 1;
          else break;
        }
        take("]");
        return output;
      }
      if (token.type === "(") { position += 1; const value = parseValue(); take(")"); return value; }
      throw new Error(`Unexpected ${token.type}`);
    };
    parseValue = () => {
      let value = parseAtom();
      while (peek()?.type === "+") { position += 1; value = String(value ?? "") + String(parseAtom() ?? ""); }
      return value;
    };
    const output = [];
    while (position < tokens.length) {
      output.push(parseValue());
      if (peek()?.type === ",") position += 1;
      else break;
    }
    if (position !== tokens.length) throw new Error("Unparsed API Call content");
    return output;
  };

  const callArguments = (text) => {
    const source = String(text || "");
    const match = /(?:dataLayer\s*\.\s*push|gtag)\s*\(/i.exec(source);
    if (!match) return null;
    const start = match.index + match[0].length;
    let depth = 1;
    let quote = null;
    let escaped = false;
    for (let index = start; index < source.length; index += 1) {
      const character = source[index];
      if (quote) {
        if (escaped) escaped = false;
        else if (character === "\\") escaped = true;
        else if (character === quote) quote = null;
        continue;
      }
      if (character === '"' || character === "'" || character === "`") { quote = character; continue; }
      if (character === "(") depth += 1;
      if (character === ")") depth -= 1;
      if (depth === 0) {
        try { return { arguments: parseLiteralList(source.slice(start, index)), complete: true }; }
        catch (error) { return { complete: false, reason: compact(error?.message || error) }; }
      }
    }
    return { complete: false, reason: "API Call text is truncated." };
  };

  const normalizeNameValues = (value) => {
    if (Array.isArray(value)) {
      const pairs = value.every((row) => row && typeof row === "object" && !Array.isArray(row) && "name" in row && "value" in row);
      if (pairs) return Object.fromEntries(value.map((row) => [String(row.name), normalizeNameValues(row.value)]));
      return value.map(normalizeNameValues);
    }
    if (!value || typeof value !== "object") return value;
    const output = {};
    for (const [key, child] of Object.entries(value)) output[key] = normalizeNameValues(child);
    return output;
  };
  const parseCell = (text) => {
    const value = String(text || "").trim();
    if (!value) return "";
    if (/^(?:\{|\[)/.test(value)) {
      try { return normalizeNameValues(parseLiteralList(value)[0]); } catch { /* retain text */ }
    }
    if (/^(?:true|false|null|-?(?:\d+\.?\d*|\.\d+))$/i.test(value)) {
      try { return parseLiteralList(value)[0]; } catch { /* retain text */ }
    }
    return value;
  };
  const mergeDetailValue = (output, key, value) => {
    const normalizedKey = compact(key).replace(/\s+/g, "_").toLowerCase();
    const expand = /^(?:event_parameters?|user_properties?|fields_to_set|config_settings_table|event_settings_table)$/i.test(normalizedKey);
    if (expand && value && typeof value === "object" && !Array.isArray(value)) Object.assign(output, value);
    else output[normalizedKey || key] = value;
  };

  const eventRows = (selector) => {
    const rows = [];
    const seen = new Set();
    for (const node of document.querySelectorAll(selector)) {
      if (!visible(node)) continue;
      const label = compact(node.innerText || node.getAttribute("aria-label"));
      const match = label.match(/^(\d+)\s+(.+?)$/s);
      if (!match || seen.has(Number(match[1]))) continue;
      seen.add(Number(match[1]));
      rows.push({ index: Number(match[1]), name: match[2].replace(/\s+Built-in trigger\s*$/i, "").trim() });
    }
    return rows.sort((left, right) => left.index - right.index);
  };
  let rows = eventRows("button");
  if (!rows.some((row) => row.index > cursorStart)) {
    fallbackUsed = true;
    rows = eventRows('[role="button"], button');
  }
  const delta = rows.filter((row) => row.index > cursorStart);
  const eventListComplete = delta.every((row, position) => row.index === cursorStart + position + 1);
  const epoch = String(cursor.epoch || globalThis.__gtmRecettePreviewEpoch || `PREVIEW-${Date.now().toString(36)}`);
  globalThis.__gtmRecettePreviewEpoch = epoch;
  const baseCompleteness = {
    event_list: eventListComplete,
    api_call: false,
    fired_list: false,
    not_fired_set: false,
    tag_details: false,
    runtime_parameters: false,
  };
  if (!delta.length) {
    return {
      epoch,
      preview_session_id: cursor.preview_session_id || null,
      cursor_start: cursorStart,
      cursor_end: cursorStart,
      events: [],
      complete: false,
      event_list_complete: eventListComplete,
      reason: "No post-cursor Preview event is visible.",
      fallback_used: fallbackUsed,
      completeness: baseCompleteness,
    };
  }

  const pause = () => new Promise((resolve) => setTimeout(resolve, 25));
  const clickText = async (name, exact = true) => {
    const candidates = [...document.querySelectorAll('button, [role="button"], [role="tab"], a, label')]
      .filter(visible)
      .filter((node) => exact ? compact(node.innerText || node.getAttribute("aria-label")) === name : compact(node.innerText || node.getAttribute("aria-label")).includes(name));
    const candidate = candidates[0];
    if (!candidate) return false;
    candidate.click();
    await pause();
    return true;
  };
  const selectEvent = async (row) => {
    const candidate = [...document.querySelectorAll('button, [role="button"]')]
      .filter(visible)
      .find((node) => new RegExp(`^${row.index}\\s+`).test(compact(node.innerText || node.getAttribute("aria-label"))));
    if (!candidate) return false;
    candidate.click();
    await pause();
    return true;
  };
  const panelText = () => {
    const panels = [...document.querySelectorAll('[role="tabpanel"]')].filter(visible);
    const root = panels.at(-1) || document.body;
    const editors = [...root.querySelectorAll(".CodeMirror")].map((node) => {
      try { return node.CodeMirror ? node.CodeMirror.getValue() : node.innerText; }
      catch { return node.innerText; }
    }).filter(Boolean);
    return String(editors.join("\n") || root.innerText || "").slice(0, 30000);
  };
  const readPanel = async (name) => {
    if (!(await clickText(name))) {
      fallbackUsed = true;
      if (!(await clickText(name, false))) return null;
    }
    return panelText();
  };
  const tagInventory = (text) => {
    const body = String(text || "");
    const firedHeading = body.search(/Tags?\s+Fired/i);
    const notHeading = body.search(/Tags?\s+Not\s+Fired/i);
    const controls = [...document.querySelectorAll('a, button, [role="button"]')]
      .filter(visible)
      .map((node) => String(node.innerText || node.getAttribute("aria-label") || "").trim())
      .filter(Boolean);
    const ignored = /^(?:Tags|Variables|Data Layer|Consent|API Call|Names|Values|Back|Close)$/i;
    const output = { fired: [], not_fired: [] };
    for (const label of controls) {
      const lines = label.split(/\r?\n/).map(compact).filter(Boolean);
      const name = lines[0] || "";
      if (!name || ignored.test(name) || /^\d+\s+/.test(name) || name.length > 300) continue;
      const location = body.indexOf(label);
      const explicitlySucceeded = /\bSucceeded\b|\bFired\b/i.test(label);
      const explicitlyNot = /\bDid not fire\b|\bNot fired\b|\bFailed\b/i.test(label);
      const fired = explicitlySucceeded || (!explicitlyNot && firedHeading >= 0 && location >= firedHeading && (notHeading < 0 || location < notHeading));
      const target = fired ? output.fired : output.not_fired;
      if (!target.some((row) => row.tag_id === name)) target.push({ tag_id: name, tag_name: name, category: tagCategory(label) });
    }
    return output;
  };
  const readDetailTable = () => {
    const output = {};
    const roots = [...document.querySelectorAll('[role="tabpanel"]')].filter(visible);
    const root = roots.at(-1) || document.body;
    for (const row of root.querySelectorAll("tr")) {
      const cells = [...row.querySelectorAll("th, td")].map((cell) => String(cell.innerText || "").trim());
      if (cells.length >= 2 && compact(cells[0])) mergeDetailValue(output, cells[0], parseCell(cells.slice(1).join("\n")));
    }
    if (!Object.keys(output).length) {
      const lines = String(root.innerText || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      for (let index = 0; index + 1 < lines.length; index += 2) mergeDetailValue(output, lines[index], parseCell(lines[index + 1]));
    }
    return output;
  };
  const readTagDetail = async (tag) => {
    if (!(await clickText(tag.tag_id)) && !(await clickText(tag.tag_id, false))) return null;
    const namesSelected = await clickText("Names");
    const configuration = readDetailTable();
    const valuesSelected = await clickText("Values");
    const runtime = readDetailTable();
    const firingText = panelText();
    await clickText("Back", false);
    return {
      ...tag,
      fired: tag.fired,
      firing_count: tag.fired ? 1 : 0,
      firing_status: /succeeded|fired/i.test(firingText) ? "Succeeded" : tag.fired ? "Fired" : "Not fired",
      configuration: namesSelected ? configuration : null,
      configuration_complete: namesSelected,
      runtime_parameters: valuesSelected ? runtime : {},
      runtime_complete: valuesSelected,
    };
  };

  const outputEvents = delta.map((row) => ({
    ...row,
    epoch,
    event_name: row.name,
    action_id: contract.action_id || null,
    fired_tags: [],
    not_fired_tags: [],
    tags: [],
    full_tag_summary: false,
    completeness: { ...baseCompleteness },
  }));
  let timedOut = false;
  let causalWindowOpen = false;
  for (const event of outputEvents) {
    if (Date.now() >= deadline) { timedOut = true; break; }
    if (!(await selectEvent(event))) continue;
    const normalizedName = event.name.toLowerCase();
    const technical = technicalName.test(event.name);
    const planned = sourceNames.has(normalizedName) || deliveryNames.has(normalizedName) || (stateOnly && /^message$/i.test(event.name));
    const needsApi = planned || !technical;
    const needsTags = wantedPanels.has("Tags") && (planned || (technical && causalWindowOpen));
    event.tag_summary_required = needsTags;
    if (needsApi && Date.now() < deadline) {
      const text = await readPanel("API Call");
      const parsed = callArguments(text);
      if (parsed?.complete) {
        event.api_call = parsed;
        event.completeness.api_call = true;
        const payloadText = JSON.stringify(parsed.arguments).toLowerCase();
        event.source_anchor_score = fieldLeaves.filter((leaf) => payloadText.includes(leaf)).length;
        const named = parsed.arguments.find((argument) => argument && typeof argument === "object" && typeof argument.event === "string");
        if (named) event.event_name = named.event;
      } else if (parsed?.reason) event.api_call_reason = parsed.reason;
    }
    if (needsTags && Date.now() < deadline) {
      const text = await readPanel("Tags");
      if (text !== null) {
        const inventory = tagInventory(text);
        event.fired_tags = inventory.fired.map((tag) => ({ ...tag, fired: true }));
        event.not_fired_tags = inventory.not_fired.map((tag) => ({ ...tag, fired: false }));
        event.full_tag_summary = true;
        event.completeness.fired_list = true;
        event.completeness.not_fired_set = true;
        const candidates = [...event.fired_tags, ...event.not_fired_tags].filter((tag) => {
          const declared = declaredTags.some((value) => value === tag.tag_id || tag.tag_id.includes(value) || value.includes(tag.tag_id));
          return declared || (!declaredTags.length && tagInScope(`${tag.tag_id} ${tag.category}`));
        });
        const concerned = candidates.filter((tag) => tag.fired);
        if (!concerned.length && candidates.length) concerned.push(candidates[0]);
        for (const tag of concerned) {
          if (Date.now() >= deadline) { timedOut = true; break; }
          const detail = await readTagDetail(tag);
          if (detail) event.tags.push(detail);
          await readPanel("Tags");
        }
        event.completeness.tag_details = concerned.length === event.tags.length;
        event.completeness.runtime_parameters = event.tags.filter((tag) => tag.fired).every((tag) => tag.runtime_complete === true);
      }
    }
    if (wantedPanels.has("Data Layer") && planned && Date.now() < deadline) {
      const text = await readPanel("Data Layer");
      const parsed = callArguments(`dataLayer.push(${text || ""})`);
      if (parsed?.complete && parsed.arguments[0] && typeof parsed.arguments[0] === "object") {
        event.data_layer_state = parsed.arguments[0];
        event.completeness.data_layer_state = true;
      }
    }
    if (wantedPanels.has("Variables") && planned && Date.now() < deadline) {
      const text = await readPanel("Variables");
      if (text !== null) {
        event.resolved_state = readDetailTable();
        event.completeness.variables = true;
      }
    }
    if (planned) causalWindowOpen = true;
    else if (!technical) causalWindowOpen = false;
  }

  const scored = outputEvents.filter((event) => Number(event.source_anchor_score) > 0);
  const bestScore = scored.length ? Math.max(...scored.map((event) => Number(event.source_anchor_score))) : 0;
  const bestAnchors = scored.filter((event) => event.source_anchor_score === bestScore);
  const relevant = outputEvents.filter((event) => event.tag_summary_required);
  const requiredApi = outputEvents.filter((event) => !technicalName.test(event.name) || sourceNames.has(event.name.toLowerCase()) || deliveryNames.has(event.name.toLowerCase()));
  const complete = !timedOut && eventListComplete && requiredApi.every((event) => event.completeness.api_call) && relevant.every((event) => event.completeness.fired_list && event.completeness.not_fired_set);
  return {
    epoch,
    preview_session_id: cursor.preview_session_id || null,
    cursor_start: cursorStart,
    cursor_end: Math.max(...delta.map((row) => row.index)),
    events: outputEvents,
    complete,
    event_list_complete: eventListComplete,
    history_stable: eventListComplete,
    fallback_used: fallbackUsed,
    reason: complete ? null : timedOut ? `Collector returned partial evidence at the ${timeoutMs} ms bound.` : "One or more required Preview components are incomplete; judge them as BLOCKED without reloading.",
    recommended_source_anchor_index: bestAnchors.length === 1 ? bestAnchors[0].index : null,
    completeness: {
      event_list: eventListComplete,
      api_call: requiredApi.every((event) => event.completeness.api_call),
      fired_list: relevant.every((event) => !wantedPanels.has("Tags") || event.completeness.fired_list),
      not_fired_set: relevant.every((event) => !wantedPanels.has("Tags") || event.completeness.not_fired_set),
      tag_details: relevant.every((event) => !wantedPanels.has("Tags") || event.completeness.tag_details),
      runtime_parameters: relevant.every((event) => !wantedPanels.has("Tags") || event.completeness.runtime_parameters),
    },
  };
})
