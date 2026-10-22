/** SEO runtime helpers: meta tag management + admin-driven runtime config. */

const RUNTIME_URL = "/api/seo/runtime";
const PAGES_URL = "/api/seo/pages";

let runtimePromise = null;
let pagesPromise = null;

export function getRuntime() {
  if (!runtimePromise) {
    runtimePromise = fetch(RUNTIME_URL)
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
  }
  return runtimePromise;
}

export function getPageMeta() {
  if (!pagesPromise) {
    pagesPromise = fetch(PAGES_URL)
      .then((r) => (r.ok ? r.json() : []))
      .catch(() => []);
  }
  return pagesPromise;
}

function upsertMeta(attr, key, content) {
  if (!content) return;
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

function upsertLink(rel, href) {
  if (!href) return;
  let el = document.head.querySelector(`link[rel="${rel}"]`);
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
}

function upsertJsonLd(data) {
  const existing = document.getElementById("seo-jsonld");
  if (existing) existing.remove();
  if (!data) return;
  const el = document.createElement("script");
  el.type = "application/ld+json";
  el.id = "seo-jsonld";
  el.textContent = JSON.stringify(data);
  document.head.appendChild(el);
}

export function absUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `${window.location.origin}${path.startsWith("/") ? "" : "/"}${path}`;
}

/**
 * Apply SEO metadata for the current view.
 * @param {object} opts
 * @param {string} opts.title       page title (without site suffix)
 * @param {string} opts.description meta description
 * @param {string} opts.ogImage     open graph image path or url
 * @param {string} opts.canonical   canonical url path
 * @param {boolean} opts.noindex    set robots noindex
 * @param {object} opts.jsonLd      schema.org payload
 */
export function applySeo({ title, description, ogImage, canonical, noindex, jsonLd, ogType = "website" } = {}) {
  const siteName = document.documentElement.dataset.siteName || "";
  const suffix = document.documentElement.dataset.titleSuffix || "";
  const fullTitle = title ? (suffix ? `${title} ${suffix}` : title) : siteName;
  if (fullTitle) document.title = fullTitle;

  upsertMeta("name", "description", description);
  upsertMeta("property", "og:title", fullTitle);
  upsertMeta("property", "og:description", description);
  upsertMeta("property", "og:type", ogType);
  upsertMeta("property", "og:site_name", siteName);
  upsertMeta("property", "og:url", absUrl(canonical || window.location.pathname));
  if (ogImage) upsertMeta("property", "og:image", absUrl(ogImage));
  upsertMeta("name", "twitter:card", "summary_large_image");
  upsertMeta("name", "twitter:title", fullTitle);
  upsertMeta("name", "twitter:description", description);
  if (ogImage) upsertMeta("name", "twitter:image", absUrl(ogImage));

  upsertLink("canonical", absUrl(canonical || window.location.pathname));

  if (noindex) upsertMeta("name", "robots", "noindex, nofollow");
  else upsertMeta("name", "robots", "index, follow");

  upsertJsonLd(jsonLd);
}

/** Load admin-managed site defaults into <html> dataset for later use. */
export async function hydrateSiteDefaults() {
  const rt = await getRuntime();
  if (!rt) return null;
  const root = document.documentElement;
  root.dataset.siteName = rt.site_name || "";
  root.dataset.titleSuffix = rt.title_suffix || "";
  root.dataset.siteUrl = rt.site_url || "";
  if (rt.google_site_verification) {
    upsertMeta("name", "google-site-verification", rt.google_site_verification);
  }
  if (rt.bing_site_verification) {
    upsertMeta("name", "msvalidate.01", rt.bing_site_verification);
  }
  return rt;
}
