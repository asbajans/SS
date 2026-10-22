import { useEffect, useState } from "react";

import { applySeo, getRuntime, hydrateSiteDefaults } from "../seo.js";

/**
 * Applies title / description / Open Graph / JSON-LD metadata for the page.
 * Everything is optional; the admin-managed defaults fill in the blanks.
 */
export default function SeoHead({
  title,
  description,
  ogImage,
  canonical,
  noindex = false,
  jsonLd = null,
  ogType = "website",
  fallbackDescription = "",
}) {
  const [rt, setRt] = useState(null);

  useEffect(() => {
    let alive = true;
    hydrateSiteDefaults().then((data) => {
      if (alive) setRt(data);
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!rt) return;
    const desc =
      description
      || fallbackDescription
      || (document.documentElement.lang === "en" ? rt.default_description_en : rt.default_description_tr)
      || "";
    applySeo({
      title,
      description: desc,
      ogImage: ogImage || rt.og_image,
      canonical: canonical || (typeof window !== "undefined" ? window.location.pathname : ""),
      noindex,
      jsonLd,
      ogType,
    });
  }, [rt, title, description, ogImage, canonical, noindex, fallbackDescription, jsonLd, ogType]);

  return null;
}

/**
 * Loads analytics (GA4 / Plausible) and AdSense scripts from admin config.
 * Renders nothing; safe to mount once in the app root.
 */
export function AnalyticsLoader() {
  const [rt, setRt] = useState(null);

  useEffect(() => {
    let alive = true;
    getRuntime().then((data) => {
      if (alive) setRt(data);
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!rt) return;
    const { analytics, ads } = rt;

    if (analytics?.enabled && analytics.id) {
      if (analytics.provider === "plausible") {
        const script = document.createElement("script");
        script.defer = true;
        script.dataset.domain = analytics.domain || analytics.id;
        script.src = "https://plausible.io/js/script.js";
        document.head.appendChild(script);
      } else {
        const gtag = document.createElement("script");
        gtag.async = true;
        gtag.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(analytics.id)}`;
        document.head.appendChild(gtag);
        window.dataLayer = window.dataLayer || [];
        window.gtag = function gtag() { window.dataLayer.push(arguments); };
        window.gtag("js", new Date());
        window.gtag("config", analytics.id, { anonymize_ip: true });
      }
    }

    if (ads?.enabled && ads.client) {
      const script = document.createElement("script");
      script.async = true;
      script.crossOrigin = "anonymous";
      script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(ads.client)}`;
      document.head.appendChild(script);
    }
  }, [rt]);

  return null;
}
