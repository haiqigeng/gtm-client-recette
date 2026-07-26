/*
 * Visible-interaction census for GTM recette case discovery.
 *
 * Evaluate once in each applicable document or same-origin frame, then call:
 *   window.__gtmRecetteCensus({ rootSelector: "header", maxItems: 500 })
 *
 * The helper discovers cases only. Execute each accepted case through a real
 * Playwright interaction and an isolated action boundary.
 */
(() => {
  "use strict";

  function normalizedText(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function accessibleName(element) {
    const ariaLabel = element.getAttribute("aria-label");
    if (ariaLabel) {
      return normalizedText(ariaLabel);
    }
    const labelledBy = element.getAttribute("aria-labelledby");
    if (labelledBy) {
      const label = labelledBy
        .split(/\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((node) => normalizedText(node.textContent))
        .filter(Boolean)
        .join(" ");
      if (label) {
        return label;
      }
    }
    if (element.labels && element.labels.length) {
      const label = Array.from(element.labels)
        .map((node) => normalizedText(node.textContent))
        .filter(Boolean)
        .join(" ");
      if (label) {
        return label;
      }
    }
    return normalizedText(
      element.getAttribute("alt") ||
        element.getAttribute("title") ||
        element.textContent
    );
  }

  function isVisible(element, includeOffscreen) {
    const style = getComputedStyle(element);
    if (
      style.display === "none" ||
      style.visibility === "hidden" ||
      Number(style.opacity) === 0
    ) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0 || element.getClientRects().length === 0) {
      return false;
    }
    if (includeOffscreen) {
      return true;
    }
    return (
      rect.bottom >= 0 &&
      rect.right >= 0 &&
      rect.top <= window.innerHeight &&
      rect.left <= window.innerWidth
    );
  }

  function cssString(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(String(value));
    }
    return String(value).replace(/["\\]/g, "\\$&");
  }

  function selectorFor(element, root) {
    if (element.id) {
      return `#${cssString(element.id)}`;
    }
    for (const attribute of ["data-testid", "data-test", "data-track", "name"]) {
      const value = element.getAttribute(attribute);
      if (value) {
        const selector = `${element.tagName.toLowerCase()}[${attribute}="${cssString(
          value
        )}"]`;
        try {
          if (root.querySelectorAll(selector).length === 1) {
            return selector;
          }
        } catch (_) {
          // Fall through to a structural selector.
        }
      }
    }

    const parts = [];
    let node = element;
    while (node && node.nodeType === Node.ELEMENT_NODE && node !== root) {
      let part = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          (candidate) => candidate.tagName === node.tagName
        );
        if (siblings.length > 1) {
          part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = parent;
      if (parts.length >= 6) {
        break;
      }
    }
    return parts.join(" > ");
  }

  function placementFor(element) {
    const placement = element.closest(
      "header,nav,footer,main,aside,form,dialog,[role=dialog],[role=navigation]"
    );
    if (!placement) {
      return "document";
    }
    return (
      placement.getAttribute("aria-label") ||
      placement.id ||
      placement.getAttribute("role") ||
      placement.tagName.toLowerCase()
    );
  }

  function trackingAttributes(element) {
    const result = {};
    for (const attribute of Array.from(element.attributes)) {
      const name = attribute.name.toLowerCase();
      if (
        name.includes("track") ||
        name.includes("analytics") ||
        name.includes("gtm")
      ) {
        result[attribute.name] = attribute.value;
      }
    }
    return result;
  }

  function census(options = {}) {
    const root = options.rootSelector
      ? document.querySelector(options.rootSelector)
      : document;
    if (!root) {
      throw new Error(`Census root not found: ${options.rootSelector}`);
    }
    const maxItems = Number.isInteger(options.maxItems)
      ? Math.max(1, options.maxItems)
      : 500;
    const selector =
      options.selector ||
      [
        "a[href]",
        "button",
        "input:not([type=hidden])",
        "select",
        "textarea",
        "summary",
        "video",
        "iframe",
        "[role=button]",
        "[role=link]",
        "[role=menuitem]",
        "[role=tab]",
        "[contenteditable=true]",
        "[data-track]",
      ].join(",");

    const items = [];
    for (const element of Array.from(root.querySelectorAll(selector))) {
      if (!isVisible(element, Boolean(options.includeOffscreen))) {
        continue;
      }
      const rect = element.getBoundingClientRect();
      items.push({
        index: items.length + 1,
        tag: element.tagName.toLowerCase(),
        role: element.getAttribute("role"),
        accessibleName: accessibleName(element),
        text: normalizedText(element.textContent).slice(0, 300),
        href: element.href || null,
        type: element.getAttribute("type"),
        disabled:
          Boolean(element.disabled) || element.getAttribute("aria-disabled") === "true",
        placement: placementFor(element),
        selector: selectorFor(element, root),
        trackingAttributes: trackingAttributes(element),
        rect: {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        },
      });
      if (items.length >= maxItems) {
        break;
      }
    }

    return {
      capturedAt: new Date().toISOString(),
      url: location.href,
      title: document.title,
      rootSelector: options.rootSelector || "document",
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio,
      },
      truncated: items.length >= maxItems,
      count: items.length,
      items,
    };
  }

  Object.defineProperty(window, "__gtmRecetteCensus", {
    value: census,
    configurable: true,
    enumerable: false,
    writable: false,
  });
})();
