import { useEffect, useRef, useState } from "react";

import { googleConfig, googleLogin } from "../api.js";
import { renderGoogleButton } from "../google.js";

export default function GoogleAuth({ onSuccess, onError, lang = "tr" }) {
  const slot = useRef(null);
  const [clientId, setClientId] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    googleConfig()
      .then((cfg) => {
        if (!alive || !cfg?.enabled) return;
        setClientId(cfg.client_id);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!clientId) return undefined;
    let alive = true;
    renderGoogleButton(slot.current, clientId, {
      hl: lang === "en" ? "en" : "tr",
      onCredential: async (credential) => {
        try {
          const data = await googleLogin(credential);
          onSuccess?.(data);
        } catch (err) {
          onError?.(err);
        }
      },
    })
      .then(() => {
        if (alive) setError(null);
      })
      .catch(() => {
        if (alive) setError("Google girişi şu anda yüklenemedi.");
      });
    return () => {
      alive = false;
    };
  }, [clientId, lang, onSuccess, onError]);

  if (!clientId) return null;

  return (
    <div className="g-auth">
      <div className="g-btn-slot" ref={slot} />
      <div className="g-divider"><span>veya</span></div>
      {error && <p className="g-note">{error}</p>}
    </div>
  );
}
