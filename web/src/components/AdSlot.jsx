import { useEffect, useState } from "react";

import { getRuntime } from "../seo.js";

/**
 * AdSense slot driven by the admin panel configuration.
 * Renders nothing when ads are disabled or not configured.
 */
export default function AdSlot({ slot = "primary", className = "", label = "Reklam" }) {
  const [rt, setRt] = useState(null);

  useEffect(() => {
    let alive = true;
    getRuntime().then((data) => {
      if (alive) setRt(data);
    });
    return () => { alive = false; };
  }, []);

  const ads = rt?.ads;
  const client = ads?.client;
  const slotId = slot === "secondary" ? ads?.slot_secondary : ads?.slot;

  useEffect(() => {
    if (!ads?.enabled || !client || !slotId) return;
    const timer = setTimeout(() => {
      try {
        window.adsbygoogle = window.adsbygoogle || [];
        window.adsbygoogle.push({});
      } catch {
        /* ads script blocked */
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [ads, client, slotId]);

  if (!ads?.enabled || !client || !slotId) return null;

  return (
    <div className={`ad-slot ${className}`.trim()}>
      <span className="ad-label">{label}</span>
      <ins
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client={client}
        data-ad-slot={slotId}
        data-full-width-responsive="true"
      />
    </div>
  );
}
