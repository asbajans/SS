import { useEffect, useRef, useState } from "react";

import { googleConfig, googleLogin } from "../api.js";
import { renderGoogleButton } from "../google.js";

export default function GoogleAuth({ onSuccess, onError, lang = "tr" }) {
  const slot = useRef(null);
  const [state, setState] = useState({ enabled: false, error: null });

  useEffect(() => {
    let alive = true;
    googleConfig()
      .then((cfg) => {
        if (!alive || !cfg?.enabled || !slot.current) return;
        renderGoogleButton(slot.current, cfg.client_id, {
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
            if (alive) setState({ enabled: true, error: null });
          })
          .catch(() => {
            if (alive) {
              setState({ enabled: false, error: "Google girişi şu anda yüklenemedi." });
            }
          });
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [lang, onSuccess, onError]);

  if (!state.enabled && !state.error) return null;

  return (
    <div className="g-auth">
      <div className="g-divider"><span>veya</span></div>
      {state.enabled && <div className="g-btn-slot" ref={slot} />}
      {state.error && <p className="g-note">{state.error}</p>}
    </div>
  );
}
