import React, { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { api } from "../api.js";
import Icon from "../icons.jsx";

const EMPTY = {
  model: "", fallbacks: "", max_tokens: 700, temperature: 0.7, rpm: 60, tpm: 200000,
  daily_budget_tokens: 3000000, monthly_budget_tokens: 30000000, cost_in_usd_per_mtok: 0,
  cost_out_usd_per_mtok: 0, enabled: true,
};

function toForm(m) {
  return { ...m, fallbacks: (m.fallbacks ?? []).join(", "), temperature: Number(m.temperature),
    cost_in_usd_per_mtok: Number(m.cost_in_usd_per_mtok), cost_out_usd_per_mtok: Number(m.cost_out_usd_per_mtok) };
}

function toPayload(f) {
  return {
    model: f.model,
    fallbacks: String(f.fallbacks).split(",").map((s) => s.trim()).filter(Boolean),
    max_tokens: Number(f.max_tokens), temperature: Number(f.temperature), rpm: Number(f.rpm),
    tpm: Number(f.tpm), daily_budget_tokens: Number(f.daily_budget_tokens),
    monthly_budget_tokens: Number(f.monthly_budget_tokens),
    cost_in_usd_per_mtok: Number(f.cost_in_usd_per_mtok), cost_out_usd_per_mtok: Number(f.cost_out_usd_per_mtok),
    enabled: Boolean(f.enabled),
  };
}

export default function Admin() {
  const user = useOutletContext();
  const [models, setModels] = useState([]);
  const [usage, setUsage] = useState(null);
  const [orModels, setOrModels] = useState([]);
  const [orErr, setOrErr] = useState(null);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [err, setErr] = useState(null);
  const [saved, setSaved] = useState(null);

  const load = useCallback(() => {
    Promise.all([
      api("/api/admin/models"),
      api("/api/admin/usage/summary"),
      api("/api/admin/openrouter/models").catch(() => []),
    ])
      .then(([m, u, orm]) => { setModels(m); setUsage(u); setOrModels(orm); })
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(load, [load]);

  if (user && !user.is_admin) return <p className="error">Bu sayfa yalnızca yöneticilere açıktır.</p>;

  const priceOf = (id) => orModels.find((x) => x.id === String(id ?? "").trim()) || null;

  function onModelChange(value) {
    const hit = priceOf(value);
    setForm((f) => ({
      ...f,
      model: value,
      ...(hit ? { cost_in_usd_per_mtok: hit.prompt_per_mtok, cost_out_usd_per_mtok: hit.completion_per_mtok } : {}),
    }));
  }

  async function reloadPrices() {
    setOrErr(null);
    try {
      setOrModels(await api("/api/admin/openrouter/models?refresh=1"));
    } catch (e) { setOrErr(e.message); }
  }

  function startEdit(m) { setEditing(m.task_key); setForm(toForm(m)); setSaved(null); setErr(null); }
  function startNew() { setEditing("__new__"); setForm({ ...EMPTY }); setSaved(null); setErr(null); }

  async function save() {
    setErr(null); setSaved(null);
    const key = editing === "__new__" ? form.task_key?.trim() : editing;
    if (!key) { setErr("Görev anahtarı zorunlu"); return; }
    try {
      await api(`/api/admin/models/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify(toPayload(form)) });
      setSaved(`${key} kaydedildi`); setEditing(null); load();
    } catch (e) { setErr(e.message); }
  }

  const num = (k, label, step = 1) => (
    <div className="field"><label>{label}</label>
      <input className="input" type="number" step={step} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
    </div>
  );

  const modelField = (label = "Model (OpenRouter)") => {
    const hit = priceOf(form.model);
    return (
      <div className="field">
        <label>{label}</label>
        <input className="input" list="or-models" placeholder="listeden seçin veya yazın" value={form.model} onChange={(e) => onModelChange(e.target.value)} />
        {hit && (
          <div className="small muted" style={{ marginTop: 4 }}>
            Maliyet: ${hit.prompt_per_mtok} giriş / ${hit.completion_per_mtok} çıkış (per Mtok)
            {hit.context_length ? ` · bağlam ${(hit.context_length / 1000).toFixed(0)}K` : ""}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div className="page-head"><div><h2>Yönetim</h2><p>Görev bazlı model konfigürasyonları, limitler ve maliyet katsayıları.</p></div>
      <div className="row">
        <button className="btn" type="button" onClick={reloadPrices}><Icon name="refresh" size={15} /> Fiyatları yenile ({orModels.length})</button>
        <button className="btn" type="button" onClick={load}><Icon name="refresh" size={15} /> Yenile</button>
        <button className="btn btn-primary" type="button" onClick={startNew}><Icon name="plus" size={15} /> Yeni görev</button>
      </div></div>

      <datalist id="or-models">
        {orModels.map((m) => (
          <option key={m.id} value={m.id}>{`${m.id} — $${m.prompt_per_mtok} / $${m.completion_per_mtok} per Mtok`}</option>
        ))}
      </datalist>

      {err && <p className="error">{err}</p>}
      {orErr && <p className="error">Model listesi: {orErr}</p>}
      {saved && <p className="ok-box">{saved}</p>}

      <div className="notice" style={{ marginBottom: 14 }}><Icon name="bell" size={15} />
        <span>Buradaki $/Mtok değerleri <strong>OpenRouter liste fiyatıdır = bizim maliyetimiz</strong>; müşteriye satış fiyatı değildir. Satış/abonelik fiyatlandırması Stripe planlarında (F5) tanımlanır.</span>
      </div>

      <div className="stat-grid">
        <div className="card stat"><div className="stat-label"><Icon name="chart" size={15} /> LLM çağrısı</div><div className="stat-value">{usage?.total_calls ?? "—"}</div><div className="stat-sub">token_usage kaydı (tüm zamanlar)</div></div>
        <div className="card stat"><div className="stat-label"><Icon name="sliders" size={15} /> Görev konfigürasyonu</div><div className="stat-value">{models.length}</div><div className="stat-sub">aktif kural seti</div></div>
        <div className="card stat"><div className="stat-label"><Icon name="box" size={15} /> OpenRouter modeli</div><div className="stat-value">{orModels.length || "—"}</div><div className="stat-sub">canlı liste (10 dk önbellek)</div></div>
      </div>

      <div className="card table-wrap">
        <table className="tbl">
          <thead><tr><th>Görev</th><th>Model</th><th className="num">max_tokens</th><th className="num">RPM</th><th className="num">Günlük bütçe</th><th className="num">Maliyet $/Mtok (g/ç)</th><th>Durum</th><th>İşlem</th></tr></thead>
          <tbody>
            {models.map((m) => (
              <React.Fragment key={m.task_key}>
                <tr>
                  <td className="mono" style={{ fontWeight: 620 }}>{m.task_key}</td><td>{m.model}</td><td className="num">{m.max_tokens}</td><td className="num">{m.rpm}</td><td className="num">${(m.daily_budget_tokens / 1_000_000).toFixed(0)}M</td><td className="num">${m.cost_in_usd_per_mtok} / ${m.cost_out_usd_per_mtok}</td>
                  <td>{m.enabled ? <span className="badge ok">açık</span> : <span className="badge">kapalı</span>}</td>
                  <td className="num"><button className="btn btn-sm" type="button" onClick={() => startEdit(m)}>Düzenle</button></td>
                </tr>
                {editing === m.task_key && (
                  <tr><td colSpan={8} style={{ padding: 0 }}>
                    <div className="model-form">
                      <div className="grid-3">
                        {modelField()}
                        <div className="field"><label>Fallbackler (virgülle, listeden seçilebilir)</label><input className="input" list="or-models" value={form.fallbacks} onChange={(e) => setForm({ ...form, fallbacks: e.target.value })} /></div>
                        {num("max_tokens", "max_tokens")}{num("temperature", "Sıcaklık", 0.1)}{num("rpm", "RPM")}{num("tpm", "TPM")}{num("daily_budget_tokens", "Günlük token bütçesi")}{num("monthly_budget_tokens", "Aylık token bütçesi")}{num("cost_in_usd_per_mtok", "$ / Mtok (giriş)", 0.001)}{num("cost_out_usd_per_mtok", "$ / Mtok (çıkış)", 0.001)}
                      </div>
                      <div className="row" style={{ marginTop: 8 }}>
                        <label className="row small" style={{ gap: 8 }}><input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> etkin</label><span style={{ flex: 1 }} /><button className="btn" type="button" onClick={() => setEditing(null)}>Vazgeç</button><button className="btn btn-primary" type="button" onClick={save}>Kaydet</button>
                      </div>
                    </div></td></tr>
                )}
              </React.Fragment>
            ))}
            {editing === "__new__" && (
              <tr><td colSpan={8} style={{ padding: 0 }}>
                <div className="model-form">
                  <div className="grid-3">
                    <div className="field"><label>Görev anahtarı (task_key)</label><input className="input" placeholder="örn: agent_act" value={form.task_key ?? ""} onChange={(e) => setForm({ ...form, task_key: e.target.value })} /></div>
                    {modelField()}
                    {num("max_tokens", "max_tokens")}
                  </div>
                  <div className="row" style={{ marginTop: 8 }}><span style={{ flex: 1 }} /><button className="btn" type="button" onClick={() => setEditing(null)}>Vazgeç</button><button className="btn btn-primary" type="button" onClick={save}>Kaydet</button></div>
                </div></td></tr>
              )}
          </tbody>
        </table>
        {models.length === 0 && !err && (
          <div style={{ padding: 18 }}><p className="muted small">Henüz model konfigürasyonu yok. “Yeni görev” ile ilk kural setini ekleyin veya simülasyonu mock modda çalıştırın.</p></div>
        )}
      </div>
    </>
  );
}
