(async () => {
  "use strict";

  const CONTRACT = "playwright-mcp-v8";
  const MAX_MS = 5000;
  if (!/^(?:tagassistant\.google\.com|tagassistant\.googleusercontent\.com)$/i.test(location.hostname)) {
    throw new Error("Install the v8 observer in the prepared Tag Assistant tab.");
  }
  if (globalThis.__gtmRecetteCollect) {
    throw new Error("The v8 observer is already installed; do not reinstall it.");
  }

  const compact = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const visible = (node) => {
    const style = getComputedStyle(node);
    return style.display !== "none" && style.visibility !== "hidden" && node.getClientRects().length > 0;
  };
  const controls = () => [...document.querySelectorAll('button, [role="button"], [role="tab"], a')]
    .filter(visible);
  const pause = () => new Promise((resolve) => setTimeout(resolve, 25));

  const clickText = async (text) => {
    const wanted = String(text).toLowerCase();
    const target = controls().find((node) => compact(node.innerText || node.getAttribute("aria-label")).toLowerCase() === wanted);
    if (!target) return false;
    target.click();
    await pause();
    return true;
  };
  const clickTag = async (name) => {
    const wanted = String(name).toLowerCase();
    const target = controls().find((node) => compact(String(node.innerText || node.getAttribute("aria-label") || "").split(/\r?\n/)[0]).toLowerCase() === wanted);
    if (!target) return false;
    target.click();
    await pause();
    return true;
  };

  const tokens = (text) => {
    const output = [];
    let index = 0;
    while (index < text.length) {
      const character = text[index];
      if (/\s/.test(character)) { index += 1; continue; }
      if ("{}[]:,()+".includes(character)) {
        output.push({ type: character, value: character });
        index += 1;
        continue;
      }
      if ('"\'`'.includes(character)) {
        const quote = character;
        let value = "";
        let closed = false;
        index += 1;
        while (index < text.length) {
          const current = text[index++];
          if (current === quote) { closed = true; break; }
          if (current !== "\\") { value += current; continue; }
          if (index >= text.length) break;
          const escaped = text[index++];
          const escapes = { n: "\n", r: "\r", t: "\t", b: "\b", f: "\f", v: "\v" };
          if (escaped === "u" && /^[0-9a-f]{4}$/i.test(text.slice(index, index + 4))) {
            value += String.fromCharCode(parseInt(text.slice(index, index + 4), 16));
            index += 4;
          } else {
            value += Object.prototype.hasOwnProperty.call(escapes, escaped) ? escapes[escaped] : escaped;
          }
        }
        if (!closed) throw new Error("Unterminated API Call string.");
        output.push({ type: "value", value });
        continue;
      }
      const number = text.slice(index).match(/^-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/i);
      if (number) {
        output.push({ type: "value", value: Number(number[0]) });
        index += number[0].length;
        continue;
      }
      const identifier = text.slice(index).match(/^[A-Za-z_$][\w$.-]*/);
      if (identifier) {
        const word = identifier[0];
        const literals = { true: true, false: false, null: null, undefined: null, NaN: null };
        output.push({
          type: "value",
          value: Object.prototype.hasOwnProperty.call(literals, word) ? literals[word] : word,
        });
        index += word.length;
        continue;
      }
      throw new Error(`Unsupported API Call token at ${index}.`);
    }
    return output;
  };

  const parseValues = (text) => {
    const input = tokens(text);
    let index = 0;
    const peek = () => input[index];
    const take = (type) => {
      const token = input[index];
      if (!token || token.type !== type) throw new Error(`Expected ${type}.`);
      index += 1;
      return token.value;
    };
    let parseValue;
    const atom = () => {
      const token = peek();
      if (!token) throw new Error("Missing API Call value.");
      if (token.type === "value") { index += 1; return token.value; }
      if (token.type === "{") {
        index += 1;
        const value = {};
        while (peek() && peek().type !== "}") {
          const key = String(take("value"));
          take(":");
          value[key] = parseValue();
          if (peek()?.type === ",") index += 1;
          else break;
        }
        take("}");
        return value;
      }
      if (token.type === "[") {
        index += 1;
        const value = [];
        while (peek() && peek().type !== "]") {
          value.push(parseValue());
          if (peek()?.type === ",") index += 1;
          else break;
        }
        take("]");
        return value;
      }
      if (token.type === "(") {
        index += 1;
        const value = parseValue();
        take(")");
        return value;
      }
      throw new Error(`Unexpected API Call token ${token.type}.`);
    };
    parseValue = () => {
      let value = atom();
      while (peek()?.type === "+") {
        index += 1;
        value = String(value ?? "") + String(atom() ?? "");
      }
      return value;
    };
    const values = [];
    while (index < input.length) {
      values.push(parseValue());
      if (peek()?.type === ",") index += 1;
      else break;
    }
    if (index !== input.length) throw new Error("Unparsed API Call content.");
    return values;
  };

  const callArguments = (text) => {
    const source = String(text || "");
    const match = /(?:dataLayer\s*\.\s*push|gtag)\s*\(/i.exec(source);
    if (!match) return { complete: false, reason: "API Call does not contain dataLayer.push or gtag." };
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
      if ('"\'`'.includes(character)) { quote = character; continue; }
      if (character === "(") depth += 1;
      if (character === ")") depth -= 1;
      if (depth !== 0) continue;
      try {
        const args = parseValues(source.slice(start, index));
        let payload = [...args].reverse().find((value) => value && typeof value === "object" && !Array.isArray(value));
        if (String(args[0]).toLowerCase() === "event" && typeof args[1] === "string") {
          payload = { event: args[1], ...(payload || {}) };
        }
        return { arguments: args, payload: payload || null, complete: true };
      } catch (error) {
        return { complete: false, reason: compact(error?.message || error) };
      }
    }
    return { complete: false, reason: "API Call text is truncated." };
  };

  const eventRows = () => {
    const seen = new Set();
    const rows = [];
    for (const node of controls()) {
      const label = compact(node.innerText || node.getAttribute("aria-label"));
      const match = label.match(/^(\d+)\s+(.+?)$/s);
      const cursor = Number(match?.[1]);
      if (!match || seen.has(cursor)) continue;
      seen.add(cursor);
      rows.push({ cursor, name: match[2].replace(/\s+Built-in trigger\s*$/i, "").trim() });
    }
    return rows.sort((left, right) => left.cursor - right.cursor);
  };

  const selectEvent = async (cursor) => {
    const target = controls().find((node) => new RegExp(`^${cursor}\\s+`).test(compact(node.innerText || node.getAttribute("aria-label"))));
    if (!target) return false;
    target.click();
    await pause();
    return true;
  };

  const panelText = () => {
    const panels = [...document.querySelectorAll('[role="tabpanel"]')].filter(visible);
    const root = panels.at(-1) || document.body;
    const editors = [...root.querySelectorAll(".CodeMirror")]
      .map((node) => node.CodeMirror?.getValue?.() || node.innerText)
      .filter(Boolean);
    return String(editors.join("\n") || root.innerText || "").slice(0, 30000);
  };

  const readPanel = async (name) => (await clickText(name) ? panelText() : null);
  const parseCell = (text) => {
    const value = String(text || "").trim();
    if (!value) return "";
    if (/^(?:\{|\[|true$|false$|null$|-?(?:\d+\.?\d*|\.\d+)$)/i.test(value)) {
      try { return parseValues(value)[0]; } catch { return value; }
    }
    return value;
  };
  const readDetailTable = () => {
    const panels = [...document.querySelectorAll('[role="tabpanel"]')].filter(visible);
    const root = panels.at(-1) || document.body;
    const output = {};
    for (const row of root.querySelectorAll("tr")) {
      const cells = [...row.querySelectorAll("th, td")].map((cell) => String(cell.innerText || "").trim());
      if (cells.length >= 2 && compact(cells[0])) output[compact(cells[0])] = parseCell(cells.slice(1).join("\n"));
    }
    if (!Object.keys(output).length) {
      const lines = String(root.innerText || "").split(/\r?\n/).map(compact).filter(Boolean)
        .filter((line) => !/^(?:Names|Values|Back|Close)$/i.test(line));
      for (let index = 0; index + 1 < lines.length; index += 2) {
        output[lines[index]] = parseCell(lines[index + 1]);
      }
    }
    return output;
  };

  const tagInventory = (text) => {
    const body = String(text || "");
    const firedHeading = body.search(/Tags?\s+Fired/i);
    const notHeading = body.search(/Tags?\s+Not\s+Fired/i);
    const ignored = /^(?:Tags|Variables|Data Layer|Consent|API Call|Names|Values|Back|Close)$/i;
    const output = [];
    for (const node of controls()) {
      const label = String(node.innerText || node.getAttribute("aria-label") || "").trim();
      const name = compact(label.split(/\r?\n/)[0]);
      if (!name || ignored.test(name) || /^\d+\s+/.test(name) || name.length > 300) continue;
      const location = body.indexOf(label);
      if (location < 0) continue;
      const explicitNot = /did not fire|not fired|failed/i.test(label);
      const fired = /succeeded|\bfired\b/i.test(label)
        || (!explicitNot && firedHeading >= 0 && location >= firedHeading && (notHeading < 0 || location < notHeading));
      const firingCount = Number(label.match(/fired\s+(\d+)\s+times?/i)?.[1] || (fired ? 1 : 0));
      if (!output.some((tag) => tag.name === name)) output.push({ name, fired, firing_count: firingCount });
    }
    return output;
  };

  const readTag = async (tag) => {
    if (!(await clickTag(tag.name))) return { ...tag, complete: false };
    const names = await clickText("Names");
    const mappings = names ? readDetailTable() : {};
    const values = await clickText("Values");
    const runtime = values ? readDetailTable() : {};
    const details = panelText();
    const count = Number(details.match(/fired\s+(\d+)\s+times?/i)?.[1] || tag.firing_count);
    await clickText("Back");
    return {
      ...tag,
      firing_count: count,
      mappings,
      runtime,
      complete: names && values,
    };
  };

  const valuesAt = (value, path) => {
    let current = [value];
    for (const part of String(path).split(".")) {
      const array = part.endsWith("[]");
      const name = array ? part.slice(0, -2) : part;
      const next = [];
      for (const candidate of current) {
        if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) continue;
        const key = Object.keys(candidate).find((item) => item.toLowerCase() === name.toLowerCase());
        if (!key) continue;
        const selected = candidate[key];
        if (array && Array.isArray(selected)) next.push(...selected);
        else if (!array) next.push(selected);
      }
      current = next;
    }
    return current;
  };
  const equal = (left, right) => typeof left === typeof right && left === right;
  const matchesSelector = (payload, selector) => {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return false;
    const anchors = selector.anchor_fields;
    if (Array.isArray(anchors) && anchors.length) {
      return anchors.filter((path) => valuesAt(payload, path).length).length >= Math.min(2, anchors.length);
    }
    return Object.entries(selector).every(([path, expected]) => {
      const actual = valuesAt(payload, path)[0];
      return Array.isArray(expected) ? expected.some((item) => equal(actual, item)) : equal(actual, expected);
    });
  };
  const technicalName = /^(?:gtm\.|message$|trigger\s*group$|container\s*loaded$|dom\s*ready$|window\s*loaded$|consent)/i;

  globalThis.__gtmRecetteCollect = async (spec) => {
    if (!spec || spec.observer_contract !== CONTRACT || !Number.isInteger(spec.preview_cursor) || !spec.selector) {
      throw new Error("Collector requires the v8 contract, integer cursor, and event selector.");
    }
    const deadline = Date.now() + MAX_MS;
    const rows = eventRows();
    const delta = rows.filter((row) => row.cursor > spec.preview_cursor);
    const contiguous = delta.every((row, index) => row.cursor === spec.preview_cursor + index + 1);
    const messages = [];
    for (const row of delta) {
      if (Date.now() >= deadline || !(await selectEvent(row.cursor))) break;
      const text = await readPanel("API Call");
      const call = text === null ? { complete: false, reason: "API Call tab unavailable." } : callArguments(text);
      const payload = call.payload || null;
      const name = String(payload?.event || row.name);
      const coreMessage = /^message$/i.test(row.name) && payload && Object.keys(payload).some((key) => !/^gtm\./i.test(key));
      messages.push({
        cursor: row.cursor,
        name,
        event_name: name,
        payload,
        arguments: call.arguments || [],
        api_complete: call.complete === true,
        api_reason: call.reason || null,
        business: coreMessage || !technicalName.test(name),
      });
    }
    const selected = messages.filter((message) => matchesSelector(message.payload, spec.selector));
    const selectedCursors = new Set(selected.map((message) => message.cursor));
    const causal = messages.filter((message, index) => {
      if (selectedCursors.has(message.cursor)) return true;
      const previousSelected = [...selectedCursors].some((cursor) => cursor < message.cursor);
      const interveningBusiness = messages.slice(0, index).some((candidate) => (
        candidate.cursor > Math.max(...[...selectedCursors].filter((cursor) => cursor < message.cursor), -1)
        && candidate.business
        && !selectedCursors.has(candidate.cursor)
      ));
      return previousSelected && !interveningBusiness && !message.business;
    });
    const tags = [];
    let tagsComplete = selected.length > 0;
    for (const message of causal) {
      if (Date.now() >= deadline || !(await selectEvent(message.cursor))) { tagsComplete = false; break; }
      const text = await readPanel("Tags");
      if (text === null) { tagsComplete = false; continue; }
      const inventory = tagInventory(text);
      for (const tag of inventory) {
        const detail = tag.fired && Date.now() < deadline ? await readTag(tag) : { ...tag, firing_count: 0, mappings: {}, runtime: {}, complete: true };
        tags.push({ ...detail, event_cursor: message.cursor, concerned: true });
        if (!detail.complete) tagsComplete = false;
        await readPanel("Tags");
      }
    }
    const completeMessages = messages.length === delta.length && messages.every((message) => message.api_complete);
    const selectedMessage = selected[0] || null;
    return {
      observer_contract: CONTRACT,
      preview_cursor: delta.at(-1)?.cursor ?? spec.preview_cursor,
      source: {
        complete: contiguous && completeMessages,
        attributable: contiguous,
        occurrence_count: selected.length,
        selected: selectedMessage ? { cursor: selectedMessage.cursor, payload: selectedMessage.payload, arguments: selectedMessage.arguments } : null,
        calls: messages,
        reason: contiguous && completeMessages ? null : "Preview chronology or API Call extraction is incomplete.",
      },
      gtm: {
        complete: tagsComplete,
        attributable: selected.length > 0,
        tags,
        reason: tagsComplete ? null : "Tags/Names/Values extraction is incomplete within five seconds.",
      },
      behavior: {
        complete: contiguous && completeMessages,
        attributable: contiguous,
        messages,
        reason: contiguous && completeMessages ? null : "Continuous Preview chronology is incomplete.",
      },
    };
  };

  return {
    observer_contract: CONTRACT,
    installed: true,
    current_cursor: eventRows().at(-1)?.cursor || 0,
    current_document_cursor: (() => {
      const rows = eventRows();
      const current = rows.at(-1)?.cursor || 0;
      const loaded = rows.filter((row) => /^window\s+loaded$/i.test(row.name));
      const completedCurrentDocument = loaded.at(-1)?.cursor === current;
      return (completedCurrentDocument ? loaded.at(-2) : loaded.at(-1))?.cursor || 0;
    })(),
    max_collection_ms: MAX_MS,
  };
})
