import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { api, fmtDate, fmtTokens } from "../api.js";
import Icon from "../icons.jsx";

const COPY = {
  tr: {
    title: "Plan & Faturalama",
    subtitle: "Abonelik ve kullanım kredilerinizi yönetin. Ödemeler Stripe üzerinden güvenle alınır.",
    currentPlan: "Mevcut plan",
    used: "Bu dönem kullanım",
    credits: "Kredi bakiyesi",
    resets: "Dönem sonu",
    freeUntil: "Ücretsiz erişim bitişi",
    freeExpired: "Ücretsiz dönem sona erdi. Devam etmek için plan yükseltin veya kredi yükleyin.",
    portal: "Faturaları yönet",
    plans: "Abonelik planları",
    packs: "Kullanım kredisi",
    perMonth: "/ay",
    once: "tek sefer",
    current: "Mevcut plan",
    choose: "Planı seç",
    buy: "Kredi al",
    soon: "Yakında",
    loading: "Yükleniyor…",
    off: "Stripe ödeme altyapısı yapılandırılmadı. Plan değişiklikleri ticari açılışta aktifleşecek; bu süreçte destek ekibiyle iletişime geçin.",
    success: "Ödeme alındı. Planınız birkaç saniye içinde güncellenecek.",
    cancel: "Ödeme iptal edildi; ücret alınmadı.",
    tokens: "token",
    agents: "ajana kadar",
    rounds: "tur derinlik",
    unlimited: "Krediler bittiğinde bakiye otomatik kullanılır.",
  },
  en: {
    title: "Plan & Billing",
    subtitle: "Manage your subscription and usage credits. Payments are securely processed by Stripe.",
    currentPlan: "Current plan",
    used: "Usage this period",
    credits: "Credit balance",
    resets: "Period ends",
    freeUntil: "Free access ends",
    freeExpired: "Your free period has ended. Upgrade your plan or buy credits to continue.",
    portal: "Manage invoices",
    plans: "Subscription plans",
    packs: "Usage credits",
    perMonth: "/mo",
    once: "one-time",
    current: "Current plan",
    choose: "Choose plan",
    buy: "Buy credits",
    soon: "Coming soon",
    loading: "Loading…",
    off: "Stripe billing is not configured yet. Plan changes will activate at commercial launch; contact support in the meantime.",
    success: "Payment received. Your plan will update within a few seconds.",
    cancel: "Checkout canceled; you were not charged.",
    tokens: "tokens",
    agents: "agents",
    rounds: "round depth",
    unlimited: "Credits are consumed automatically after the plan budget.",
  },
};

const NAMES = {
  tr: { free: "Ücretsiz", starter: "Başlangıç", pro: "Pro" },
  en: { free: "Free", starter: "Starter", pro: "Pro" },
};

export default function Billing() {
  const user = useOutletContext();
  const [lang, setLang] = useState(() => localStorage.getItem("ss_lang") || "tr");
  const [plans, setPlans] = useState([]);
  const [packs, setPacks] = useState([]);
  const [me, setMe] = useState(null);
  const [stripeOn, setStripeOn] = useState(false);
  const [checkout, setCheckout] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(null);
  const t = COPY[lang] ?? COPY.tr;
  const names = NAMES[lang] ?? NAMES.tr;

  useEffect(() => {
    localStorage.setItem("ss_lang", lang);
  }, [lang]);

  useEffect(() => {
    const state = new URLSearchParams(window.location.search).get("checkout");
    if (state === "success" || state === "cancel") setCheckout(state);
    Promise.all([api("/api/billing/plans"), api("/api/billing/me")])
      .then(([catalog, mine]) => {
        setPlans(catalog.plans ?? []);
        setPacks(catalog.credit_packs ?? []);
        setStripeOn(Boolean(catalog.checkout_enabled));
        setMe(mine);
      })
      .catch((e) => setErr(e.message));
  }, []);

  async function startCheckout(payload) {
    setErr(null);
    setBusy(payload.plan ?? payload.credit_pack);
    try {
      const { url } = await api("/api/billing/checkout", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      window.location.href = url;
    } catch (e) {
      setErr(e.message);
      setBusy(null);
    }
  }

  async function openPortal() {
    setErr(null);
    setBusy("portal");
    try {
      const { url } = await api("/api/billing/portal", { method: "POST" });
      window.location.href = url;
    } catch (e) {
      setErr(e.message);
      setBusy(null);
    }
  }

  const current = me?.plan ?? user?.plan ?? "free";
  const budget = me?.monthly_token_budget ?? 0;
  const used = me?.monthly_token_used ?? 0;
  const pct = budget > 0 ? Math.min(100, Math.round((used / budget) * 100)) : 0;
  const credits = me?.credit_balance ?? 0;

  return (
    <>
      <div className="page-head">
        <div>
          <h2>{t.title}</h2>
          <p>{t.subtitle}</p>
        </div>
        <button className="btn btn-sm" type="button" onClick={() => setLang(lang === "tr" ? "en" : "tr")}>
          {lang === "tr" ? "EN" : "TR"}
        </button>
      </div>

      {err && <p className="error">{err}</p>}
      {checkout === "success" && <div className="notice"><Icon name="check" size={15} /><span>{t.success}</span></div>}
      {checkout === "cancel" && <div className="notice"><Icon name="x" size={15} /><span>{t.cancel}</span></div>}

      <div className="card card-pad">
        <div className="billing-summary">
          <div>
            <div className="stat-label"><Icon name="card" size={14} /> {t.currentPlan}</div>
            <div className="stat-value">{names[current] ?? current}</div>
            {me?.billing_status && me.billing_status !== "active" && (
              <div className="badge warn no-dot">{me.billing_status}</div>
            )}
            {me?.free_until && (
              <div className="badge warn no-dot">{t.freeUntil}: {fmtDate(me.free_until)}</div>
            )}
          </div>
          <div>
            <div className="stat-label"><Icon name="activity" size={14} /> {t.used}</div>
            <div className="stat-value">{fmtTokens(used)} <span className="muted">/ {fmtTokens(budget)}</span></div>
          </div>
          <div>
            <div className="stat-label"><Icon name="chart" size={14} /> {t.credits}</div>
            <div className="stat-value">{fmtTokens(credits)}</div>
          </div>
        </div>
        <div className="usage-bar"><div className="usage-fill" style={{ width: `${pct}%` }} /></div>
        <div className="usage-meta">
          <span>{pct}% {t.tokens}</span>
          <span>{t.resets}: {me?.billing_period_end ? fmtDate(me.billing_period_end) : "—"}</span>
          {me?.has_customer && (
            <button className="btn btn-sm" type="button" disabled={busy === "portal"} onClick={openPortal}>
              {busy === "portal" ? t.loading : t.portal}
            </button>
          )}
        </div>
      </div>

      <h3 className="section-title">{t.plans}</h3>
      <div className="grid-3">
        {plans.map((p) => {
          const isCurrent = p.key === current;
          const disabled = isCurrent || !stripeOn || !p.checkout_enabled || Boolean(busy);
          const label = isCurrent ? t.current : !stripeOn || !p.checkout_enabled ? t.soon : t.choose;
          return (
            <div className={`card plan-card${isCurrent ? " current" : ""}`} key={p.key}>
              {isCurrent && <span className="plan-tag">{t.current.toUpperCase()}</span>}
              <h3>{names[p.key] ?? p.key}</h3>
              <div className="plan-price">
                ${p.price}
                <span> {p.price > 0 ? t.perMonth : ""}</span>
              </div>
              <ul className="plan-feats">
                <li><Icon name="check" size={15} /> {fmtTokens(p.token_budget)} {t.tokens} / {lang === "tr" ? "ay" : "mo"}</li>
                <li><Icon name="check" size={15} /> {p.agents} {t.agents}</li>
                <li><Icon name="check" size={15} /> {p.rounds} {t.rounds}</li>
              </ul>
              <button
                className={`btn${isCurrent ? "" : " btn-primary"} btn-block`}
                type="button"
                disabled={disabled}
                onClick={() => startCheckout({ plan: p.key })}
              >
                {busy === p.key ? t.loading : label}
              </button>
            </div>
          );
        })}
      </div>

      {packs.length > 0 && (
        <>
          <h3 className="section-title">{t.packs}</h3>
          <div className="grid-2">
            {packs.map((p) => (
              <div className="card card-pad credit-pack" key={p.key}>
                <div>
                  <h3>{fmtTokens(p.tokens)} {t.tokens}</h3>
                  <p className="muted">{t.unlimited}</p>
                </div>
                <div className="credit-pack-side">
                  <div className="plan-price">${p.price} <span>{t.once}</span></div>
                  <button
                    className="btn btn-primary"
                    type="button"
                    disabled={!stripeOn || !p.checkout_enabled || Boolean(busy)}
                    onClick={() => startCheckout({ credit_pack: p.key })}
                  >
                    {busy === p.key ? t.loading : !stripeOn || !p.checkout_enabled ? t.soon : t.buy}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {me?.free_expired && <div className="notice"><Icon name="bell" size={15} /><span>{t.freeExpired}</span></div>}
      {!stripeOn && <div className="notice"><Icon name="card" size={15} /><span>{t.off}</span></div>}
    </>
  );
}
