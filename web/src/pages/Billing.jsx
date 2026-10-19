import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { api } from "../api.js";
import Icon from "../icons.jsx";

const TR_NAME = { free: "Ücretsiz", starter: "Başlangıç", pro: "Pro" };

export default function Billing() {
  const user = useOutletContext();
  const [plans, setPlans] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api("/api/billing/plans").then(setPlans).catch((e) => setErr(e.message));
  }, []);

  const current = user?.plan ?? "free";

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Plan &amp; Faturalama</h2>
          <p>
            Mevcut planınız: <strong>{TR_NAME[current] ?? current}</strong>. Ödemeler
            Stripe abonelik altyapısı üzerinden yürütülür.
          </p>
        </div>
      </div>

      {err && <p className="error">{err}</p>}

      <div className="grid-3">
        {plans.map((p) => {
          const isCurrent = p.key === current;
          return (
            <div className={`card plan-card${isCurrent ? " current" : ""}`} key={p.key}>
              {isCurrent && <span className="plan-tag">MEVCUT</span>}
              <h3>{TR_NAME[p.key] ?? p.key}</h3>
              <div className="plan-price">
                ${p.price}
                <span> / ay</span>
              </div>
              <ul className="plan-feats">
                <li><Icon name="check" size={15} /> {Math.round(p.token_budget / 1_000_000)}M token / ay</li>
                <li><Icon name="check" size={15} /> {p.agents} ajan&apos;a kadar</li>
                <li><Icon name="check" size={15} /> {p.rounds} tura kadar derinlik</li>
              </ul>
              <button
                className={`btn${isCurrent ? "" : " btn-primary"} btn-block`}
                type="button"
                disabled
                title="Stripe Checkout F5'te bağlanacak"
              >
                {isCurrent ? "Mevcut plan" : "Planı seç"}
              </button>
            </div>
          );
        })}
      </div>

      <div className="notice">
        <Icon name="card" size={15} />
        <span>
          Stripe ödeme entegrasyonu (Checkout + webhook senkronizasyonu) ticari açılış
          fazında aktifleşecek; plan değişiklikleri şu an manuel olarak yönetiliyor.
        </span>
      </div>
    </>
  );
}
