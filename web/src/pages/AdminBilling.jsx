import { useCallback, useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";

import { api, fmtCost, fmtDate, fmtTokens } from "../api.js";
import Icon from "../icons.jsx";

function planForm(p) {
  return {
    price: Number(p.price ?? 0),
    budget_m: Number(p.token_budget ?? 0) / 1_000_000,
    agents: Number(p.agents ?? 0),
    rounds: Number(p.rounds ?? 0),
    free_days: Number(p.free_days ?? 0),
    stripe_price_id: p.stripe_price_id ?? "",
    is_active: Boolean(p.is_active),
  };
}

function packForm(p) {
  return {
    tokens: Number(p.tokens ?? 0),
    price: Number(p.price ?? 0),
    stripe_price_id: p.stripe_price_id ?? "",
    is_active: Boolean(p.is_active),
  };
}

export default function AdminBilling() {
  const user = useOutletContext();
  const [plans, setPlans] = useState([]);
  const [packs, setPacks] = useState([]);
  const [planEdits, setPlanEdits] = useState({});
  const [packEdits, setPackEdits] = useState({});
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [err, setErr] = useState(null);
  const [saved, setSaved] = useState(null);
  const [busy, setBusy] = useState(null);

  const loadUsers = useCallback((search) => {
    const qs = new URLSearchParams({ limit: "200" });
    if (search) qs.set("q", search);
    return api(`/api/admin/users?${qs}`).then((data) => {
      setUsers(data.users ?? []);
      setTotal(data.total ?? 0);
    });
  }, []);

  const load = useCallback(() => {
    setErr(null);
    Promise.all([api("/api/admin/plans"), loadUsers(query)])
      .then(([catalog]) => {
        setPlans(catalog.plans ?? []);
        setPacks(catalog.credit_packs ?? []);
        const pm = {};
        (catalog.plans ?? []).forEach((p) => { pm[p.key] = planForm(p); });
        setPlanEdits(pm);
        const cm = {};
        (catalog.credit_packs ?? []).forEach((p) => { cm[p.key] = packForm(p); });
        setPackEdits(cm);
      })
      .catch((e) => setErr(e.message));
  }, [query, loadUsers]);

  useEffect(load, [load]);

  if (user && !user.is_admin) return <p className="error">Bu sayfa yalnızca yöneticilere açıktır.</p>;

  function setPlan(key, field, value) {
    setPlanEdits((prev) => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
  }

  function setPack(key, field, value) {
    setPackEdits((prev) => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
  }

  async function savePlan(key) {
    const f = planEdits[key];
    setBusy(`plan:${key}`); setErr(null); setSaved(null);
    try {
      await api(`/api/admin/plans/${encodeURIComponent(key)}`, {
        method: "PUT",
        body: JSON.stringify({
          price: Number(f.price),
          token_budget: Math.round(Number(f.budget_m) * 1_000_000),
          agents: Number(f.agents),
          rounds: Number(f.rounds),
          free_days: key === "free" ? Number(f.free_days) : 0,
          stripe_price_id: f.stripe_price_id,
          is_active: Boolean(f.is_active),
        }),
      });
      setSaved(`${key} planı kaydedildi; mevcut kullanıcı bütçeleri güncellendi.`);
      load();
    } catch (e) { setErr(e.message); }
    setBusy(null);
  }

  async function savePack(key) {
    const f = packEdits[key];
    setBusy(`pack:${key}`); setErr(null); setSaved(null);
    try {
      await api(`/api/admin/credit-packs/${encodeURIComponent(key)}`, {
        method: "PUT",
        body: JSON.stringify({
          tokens: Number(f.tokens),
          price: Number(f.price),
          stripe_price_id: f.stripe_price_id,
          is_active: Boolean(f.is_active),
        }),
      });
      setSaved(`${key} kredi paketi kaydedildi.`);
      load();
    } catch (e) { setErr(e.message); }
    setBusy(null);
  }

  function search(e) {
    e.preventDefault();
    setQuery(q.trim());
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Ticari yönetim</h2>
          <p>Plan fiyatları, kotalar, ücretsiz dönem, kredi paketleri ve kullanıcı harcamaları.</p>
        </div>
        <div className="row">
          <Link className="btn" to="/app/admin"><Icon name="arrowLeft" size={15} /> Yönetim</Link>
          <button className="btn" type="button" onClick={load}><Icon name="refresh" size={15} /> Yenile</button>
        </div>
      </div>

      {err && <p className="error">{err}</p>}
      {saved && <p className="ok-box">{saved}</p>}

      <div className="page-head" style={{ marginTop: 18 }}>
        <div><h2>Planlar</h2><p>Fiyatlar USD; ücretsiz dönem 0 = süresiz. Değişiklikler kayıtlı kullanıcı bütçelerine uygulanır.</p></div>
      </div>

      <div className="card table-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Plan</th><th className="num">Fiyat ($/ay)</th><th className="num">Token (M)</th>
              <th className="num">Ajan</th><th className="num">Tur</th><th className="num">Ücretsiz gün</th>
              <th>Stripe price ID</th><th>Durum</th><th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => {
              const f = planEdits[p.key];
              if (!f) return null;
              return (
                <tr key={p.key}>
                  <td className="mono" style={{ fontWeight: 650 }}>{p.key}</td>
                  <td className="num"><input className="input" type="number" min={0} step="0.01" style={{ width: 90 }} value={f.price} onChange={(e) => setPlan(p.key, "price", e.target.value)} /></td>
                  <td className="num"><input className="input" type="number" min={0} step="0.1" style={{ width: 90 }} value={f.budget_m} onChange={(e) => setPlan(p.key, "budget_m", e.target.value)} /></td>
                  <td className="num"><input className="input" type="number" min={1} max={300} style={{ width: 80 }} value={f.agents} onChange={(e) => setPlan(p.key, "agents", e.target.value)} /></td>
                  <td className="num"><input className="input" type="number" min={1} max={80} style={{ width: 70 }} value={f.rounds} onChange={(e) => setPlan(p.key, "rounds", e.target.value)} /></td>
                  <td className="num"><input className="input" type="number" min={0} max={3650} style={{ width: 80 }} disabled={p.key !== "free"} value={p.key === "free" ? f.free_days : 0} onChange={(e) => setPlan(p.key, "free_days", e.target.value)} /></td>
                  <td><input className="input mono" placeholder="price_..." style={{ minWidth: 150 }} value={f.stripe_price_id} onChange={(e) => setPlan(p.key, "stripe_price_id", e.target.value)} /></td>
                  <td><label className="row small" style={{ gap: 6 }}><input type="checkbox" checked={f.is_active} onChange={(e) => setPlan(p.key, "is_active", e.target.checked)} /> aktif</label></td>
                  <td><button className="btn btn-sm btn-primary" type="button" disabled={busy === `plan:${p.key}`} onClick={() => savePlan(p.key)}>{busy === `plan:${p.key}` ? "…" : "Kaydet"}</button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {plans.length === 0 && !err && <div style={{ padding: 18 }}><p className="muted small">Plan bulunamadı.</p></div>}
      </div>

      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Kredi paketleri</h2><p>Token paketleri tek seferlik Stripe ödemesiyle satılır.</p></div>
      </div>

      <div className="card table-wrap">
        <table className="tbl">
          <thead><tr><th>Paket</th><th className="num">Token</th><th className="num">Fiyat ($)</th><th>Stripe price ID</th><th>Durum</th><th>İşlem</th></tr></thead>
          <tbody>
            {packs.map((p) => {
              const f = packEdits[p.key];
              if (!f) return null;
              return (
                <tr key={p.key}>
                  <td className="mono" style={{ fontWeight: 650 }}>{p.key}</td>
                  <td className="num"><input className="input" type="number" min={1} step={100000} style={{ width: 130 }} value={f.tokens} onChange={(e) => setPack(p.key, "tokens", e.target.value)} /></td>
                  <td className="num"><input className="input" type="number" min={0} step="0.01" style={{ width: 90 }} value={f.price} onChange={(e) => setPack(p.key, "price", e.target.value)} /></td>
                  <td><input className="input mono" placeholder="price_..." style={{ minWidth: 160 }} value={f.stripe_price_id} onChange={(e) => setPack(p.key, "stripe_price_id", e.target.value)} /></td>
                  <td><label className="row small" style={{ gap: 6 }}><input type="checkbox" checked={f.is_active} onChange={(e) => setPack(p.key, "is_active", e.target.checked)} /> aktif</label></td>
                  <td><button className="btn btn-sm btn-primary" type="button" disabled={busy === `pack:${p.key}`} onClick={() => savePack(p.key)}>{busy === `pack:${p.key}` ? "…" : "Kaydet"}</button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {packs.length === 0 && !err && <div style={{ padding: 18 }}><p className="muted small">Kredi paketi bulunamadı.</p></div>}
      </div>

      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Kullanıcılar</h2><p>{total} kullanıcı; token harcamaları token_usage kayıtlarından toplanır.</p></div>
        <form className="row" onSubmit={search}>
          <input className="input" placeholder="E-posta ara" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 200 }} />
          <button className="btn" type="submit">Ara</button>
        </form>
      </div>

      <div className="card table-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>E-posta</th><th>Plan</th><th>Ücretsiz bitiş</th>
              <th className="num">Bu dönem</th><th className="num">Toplam token</th>
              <th className="num">Toplam maliyet</th><th className="num">Çağrı</th>
              <th className="num">Kredi</th><th>Kayıt</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.email}{u.is_admin ? <span className="badge run no-dot" style={{ marginLeft: 8 }}>admin</span> : null}</td>
                <td><span className="badge no-dot">{u.plan}</span></td>
                <td>
                  {u.free_until
                    ? <span className={`badge${u.free_expired ? " bad" : " ok"}`}>{u.free_expired ? "doldu" : fmtDate(u.free_until)}</span>
                    : <span className="muted">—</span>}
                </td>
                <td className="num">{fmtTokens(u.monthly_token_used)} / {fmtTokens(u.monthly_token_budget)}</td>
                <td className="num">{fmtTokens(u.tokens_total)}</td>
                <td className="num">{fmtCost(u.cost_total_usd)}</td>
                <td className="num">{u.calls_total}</td>
                <td className="num">{fmtTokens(u.credit_balance)}</td>
                <td className="small muted">{fmtDate(u.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && !err && <div style={{ padding: 18 }}><p className="muted small">Kullanıcı bulunamadı.</p></div>}
      </div>
    </>
  );
}
