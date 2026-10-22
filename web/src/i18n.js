import { useEffect, useState } from "react";

import { EN } from "./dict.js";

const LANG_KEY = "ss_lang";
const ATTRS = ["placeholder", "title", "aria-label"];

const textState = new WeakMap();
const attrState = new WeakMap();

let lang = "tr";
let observer = null;
let pending = false;

export function getLang() {
  return lang;
}

export function translate(text) {
  return lang === "en" ? (EN[text] ?? text) : text;
}

function applyTextNode(node) {
  const current = node.nodeValue;
  if (!current || !current.trim()) return;
  let entry = textState.get(node);
  if (!entry) {
    entry = { src: current, applied: null };
    textState.set(node, entry);
  } else if (current !== entry.applied && current !== entry.src) {
    entry.src = current;
    entry.applied = null;
  }
  if (lang !== "en") {
    if (entry.applied && node.nodeValue !== entry.src) {
      node.nodeValue = entry.src;
      entry.applied = null;
    }
    return;
  }
  const trimmed = entry.src.trim();
  const dict = EN[trimmed];
  if (!dict) return;
  const index = entry.src.indexOf(trimmed);
  const next = entry.src.slice(0, index) + dict + entry.src.slice(index + trimmed.length);
  if (node.nodeValue !== next) node.nodeValue = next;
  entry.applied = next;
}

function applyElement(element) {
  for (const attr of ATTRS) {
    const value = element.getAttribute(attr);
    if (!value) continue;
    let store = attrState.get(element);
    if (!store) {
      store = {};
      attrState.set(element, store);
    }
    let entry = store[attr];
    if (!entry) {
      entry = { src: value, applied: null };
      store[attr] = entry;
    } else if (value !== entry.applied && value !== entry.src) {
      entry.src = value;
      entry.applied = null;
    }
    if (lang !== "en") {
      if (entry.applied && element.getAttribute(attr) !== entry.src) {
        element.setAttribute(attr, entry.src);
        entry.applied = null;
      }
      continue;
    }
    const dict = EN[value.trim()];
    if (!dict) continue;
    const next = value.replace(value.trim(), dict);
    if (element.getAttribute(attr) !== next) element.setAttribute(attr, next);
    entry.applied = next;
  }
}

function walk(node) {
  if (!node) return;
  if (node.nodeType === Node.TEXT_NODE) {
    applyTextNode(node);
    return;
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return;
  const tag = node.tagName;
  if (tag === "SCRIPT" || tag === "STYLE" || tag === "TEXTAREA" || tag === "NOSCRIPT") return;
  applyElement(node);
  const children = node.childNodes;
  for (let i = 0; i < children.length; i += 1) walk(children[i]);
}

export function applyTranslations(root) {
  const target = root ?? document.body;
  if (target) walk(target);
}

function schedule() {
  if (pending) return;
  pending = true;
  window.requestAnimationFrame(() => {
    pending = false;
    applyTranslations(document.body);
  });
}

export function setLang(next) {
  lang = next === "en" ? "en" : "tr";
  localStorage.setItem(LANG_KEY, lang);
  document.documentElement.lang = lang;
  applyTranslations(document.body);
  window.dispatchEvent(new CustomEvent("ss_lang_change", { detail: lang }));
}

export function toggleLang() {
  setLang(lang === "en" ? "tr" : "en");
}

export function useLang() {
  const [value, setValue] = useState(getLang());
  useEffect(() => {
    const handler = (event) => setValue(event.detail);
    window.addEventListener("ss_lang_change", handler);
    return () => window.removeEventListener("ss_lang_change", handler);
  }, []);
  return [value, toggleLang];
}

export function initI18n() {
  lang = localStorage.getItem(LANG_KEY) === "en" ? "en" : "tr";
  document.documentElement.lang = lang;
  applyTranslations(document.body);
  if (!observer && typeof MutationObserver !== "undefined") {
    observer = new MutationObserver(schedule);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ATTRS,
    });
  }
  window.addEventListener("storage", (event) => {
    if (event.key !== LANG_KEY) return;
    lang = localStorage.getItem(LANG_KEY) === "en" ? "en" : "tr";
    document.documentElement.lang = lang;
    applyTranslations(document.body);
  });
}
