/** Product analytics: GA4 event tracking + server-side event drain. */

import { api } from "./api.js";

const NAME_RE = /[^a-z0-9_]+/g;

// Events that the backend delivers through the GA4 Measurement Protocol.
// Sending them from the browser as well would double count them.
export const SERVER_OWNED_EVENTS = [
  "sign_up",
  "login",
  "purchase",
  "subscription_renew",
  "plan_change",
  "checkout_start",
];

/** True when analytics is enabled in the admin panel. */
export function analyticsEnabled() {
  return document.documentElement.dataset.analytics === "on";
}

/** True when the backend delivers conversions server-side (preferred). */
export function serverSideEnabled() {
  return document.documentElement.dataset.analyticsServer === "on";
}

/** Normalize an event name to GA4 snake_case. */
export function normalizeName(name) {
  return (name || "").toLowerCase().replace(NAME_RE, "_").replace(/^_+|_+$/g, "").slice(0, 64);
}

/**
 * Push an event to GA4.
 * Safe to call before gtag.js finished loading: the event is queued in
 * dataLayer and processed as soon as the tag script arrives.
 */
export function trackEvent(name, params = {}) {
  const eventName = normalizeName(name);
  if (!eventName) return false;
  // Backend-owned conversions are sent by the server (Measurement Protocol).
  if (serverSideEnabled() && SERVER_OWNED_EVENTS.includes(eventName)) return false;
  const payload = { ...params };
  try {
    window.dataLayer = window.dataLayer || [];
    if (typeof window.gtag === "function") {
      window.gtag("event", eventName, payload);
    } else {
      window.dataLayer.push({ event: eventName, ...payload });
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Send server-side events (signup, purchase, ...) that were queued in the
 * database, then acknowledge them so they are not sent twice.
 */
export async function flushServerEvents() {
  if (!analyticsEnabled()) return 0;
  // Server-side delivery is already handled by the backend.
  if (serverSideEnabled()) return 0;
  try {
    const { events } = await api("/api/analytics/events");
    if (!events || events.length === 0) return 0;
    const ids = [];
    events.forEach((event) => {
      if (trackEvent(event.name, event.params || {})) ids.push(event.id);
    });
    if (ids.length) {
      await api("/api/analytics/events/ack", {
        method: "POST",
        body: JSON.stringify({ ids }),
      });
    }
    return ids.length;
  } catch {
    return 0;
  }
}

/** Record an activity that only the browser knows about (also stored server side). */
export async function trackClientEvent(name, params = {}) {
  const eventName = normalizeName(name);
  if (!eventName) return false;
  trackEvent(eventName, params);
  try {
    await api("/api/analytics/events", {
      method: "POST",
      body: JSON.stringify({ name: eventName, params }),
    });
    return true;
  } catch {
    return false;
  }
}
