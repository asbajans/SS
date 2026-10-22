import { useCallback, useEffect, useState } from "react";

import { api } from "../api.js";
import Icon from "../icons.jsx";

const PROVIDERS = [
  {
    key: "ga4",
    name: "Google Analytics 4",
    desc: "Custom dimension ve key event'leri otomatik oluşturur; trafik ve ciro raporlarını çeker.",
    scopes: ["analytics.edit", "analytics.readonly", "analytics.manage"],
    configHint: "property_id: GA4 property numarası (örn. 123456789)",
  },
  {
    key: "search_console",
    name: "Search Console",
    desc: "Sitemap gönderir ve arama performansını (tıklama, gösterim) raporlar.",
    scopes: ["webmasters"],
    configHint: "site_url: https://app.socialsimulator.com.tr (siteUrl-prefix biçimi)",
  },
  {
    key: "google_ads",
    name: "Google Ads",
    desc: "Dönüşüm (conversion) işlemlerini oluşturur ve kampanya harcamasını raporlar.",
    scopes: ["adwords"],
    configHint: "customer_id: 123-456-7890",
  },
  {
    key: "tag_manager",
    name: "Tag Manager",
    desc: "Container'a GA4 config tag'i ekler ve container versiyonunu yayınlar.",
    scopes: ["tagmanager.edit", "tagmanager.manage"],
    configHint: "container_id: GTM-XXXXXXX",
  },
];

export default function AdminGoogle() {
  const [data, setData] = useState(null);
  const [ga4, setGa4] = useState({ measurement_id: "", api_secret: "", property_id: "", server_side: true });
  const [queue, setQueue] = useState(null);
  const [ga4Report, setGa4Report] = useState(null);
  const [scReport, setScReport] = useState(null);
  const [adsReport, setAdsReport] = useState(null);
  const [forms, setForms] = useState({});
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await api("/api/admin/google/integrations");
      setData(res);
      setGa4({
        measurement_id: res.ga4?.measurement_id || "",
        api_secret: "",
        property_id: res.ga4?.property_id || "",
        server_side: res.ga4?.server_side !== false,
      });
      const next = {};
      res.integrations.forEach((i) => { next[i.provider] = { ...i, configText: JSON.stringify(i.config || {}, null, 2) }; });
      setForms(next);
    } catch (e) {
      setErr(e.message);
    }
  }, []);

  const loadQueue = useCallback(async () => {
    try { setQueue(await api("/api/admin/google/ga4/queue")); } catch { /* ignore */ }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadQueue(); }, [loadQueue]);

  async function run(key, fn) {
    setErr(null); setMsg(null); setBusy(key);
    try {
      const res = await fn();
      if (res?.ok === false && res?.error) setErr(res.error);
      else setMsg(`${key} tamamlandi`);
      return res;
    } catch (e) {
      setErr(e.message);
      return null;
    } finally {
      setBusy("");
    }
  }

  async function saveIntegration(provider) {
    const form = forms[provider] || {};
    let config = {};
    try { config = JSON.parse(form.configText || "{}"); } catch { setErr("config JSON geçersiz"); return; }
    await run(provider, async () => {
      const res = await api(`/api/admin/google/integrations/${provider}`, {
        method: "PUT",
        body: JSON.stringify({
          enabled: Boolean(form.enabled),
          client_id: form.client_id || "",
          client_secret: form.client_secret || "",
          refresh_token: form.refresh_token || "",
          config,
        }),
      });
      await load();
      return { ok: true, res };
    });
  }

  async function saveGa4() {
    await run("ga4", async () => {
      await api("/api/admin/google/ga4", {
        method: "PUT",
        body: JSON.stringify({
          analytics_id: ga4.measurement_id,
          ga4_api_secret: ga4.api_secret,
          ga4_property_id: ga4.property_id,
          ga4_server_side: ga4.server_side,
        }),
      });
      await load();
      return { ok: true };
    });
  }

  async function ga4Setup() {
    await run("ga4_setup", async () => {
      const res = await api("/api/admin/google/ga4/setup", {
        method: "POST",
        body: JSON.stringify({
          property_id: ga4.property_id,
          create_dimensions: true,
          create_key_events: true,
        }),
      });
      setMsg(`Oluşturuldu: ${(res.created || []).join(", ") || "yok"} | Atlanan: ${(res.skipped || []).join(", ") || "-"}`);
      if ((res.errors || []).length) setErr(res.errors.join(" | "));
      return { ok: true };
    });
  }

  async function ga4Test() {
    await run("ga4_test", async () => {
      const res = await api("/api/admin/google/ga4/test-event", { method: "POST" });
      if (res.ok === false) {
        setErr(`GA4 reddetti: ${res.error || JSON.stringify(res)}`);
        return { ok: true };
      }
      setMsg(
        `'ga4_test' olayi gonderildi (client_id: ${res.client_id}). ` +
          "GA4 > Yonetici > DebugView > 'Sunucudan' sekmesinde 1-2 dakikada gorunur. " +
          "DebugView sadece acikken gelen olaylari gosterir; kacirdiysaniz Realtime raporuna bakin.",
      );
      return { ok: true };
    });
  }

  async function submitSitemap() {
    await run("sitemap", async () => {
      const res = await api("/api/admin/google/search-console/submit", {
        method: "POST",
        body: JSON.stringify({ sitemap_url: "" }),
      });
      setMsg(`Sitemap gönderildi: ${res.sitemap}`);
      return { ok: true };
    });
  }

  const setForm = (provider, key, value) =>
    setForms((f) => ({ ...f, [provider]: { ...f[provider], [key]: value } }));

  if (!data) return <p className="muted small">Yükleniyor…</p>;

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Google entegrasyonları</h2>
          <p>
            Analytics, Search Console, Ads ve Tag Manager API bağlantıları. Tüm kurulum ve
            raporlama buradan yapılır; tarayıcı etiketine bağımlı kalmaz.
          </p>
        </div>
        <button className="btn btn-sm" type="button" onClick={load}>Yenile</button>
      </div>

      {err && <p className="error">{err}</p>}
      {msg && <p className="ok-box">{msg}</p>}

      {/* ---------- GA4 server-side ---------- */}
      <div className="card card-pad" style={{ marginTop: 16 }}>
        <div className="card-head">
          <div>
            <h3>GA4 sunucu taraflı ölçüm</h3>
            <p className="muted small">
              Measurement Protocol ile olaylar sunucudan gönderilir. Reklam engelleyicilerden
              etkilenmez, kullanıcı sekmeyi kapatırsa olay yine kaydedilir.
            </p>
          </div>
          <span className={`badge ${ga4.server_side ? "ok" : ""}`}>
            {ga4.server_side ? "sunucu modu" : "tarayıcı modu"}
          </span>
        </div>
        <div className="grid-2">
          <div className="field">
            <label>Measurement ID</label>
            <input className="input" value={ga4.measurement_id} placeholder="G-XXXXXXXXXX"
              onChange={(e) => setGa4({ ...ga4, measurement_id: e.target.value })} />
            <div className="hint">GA4 &gt; Yönetici &gt; Mülk Ayarları &gt; Veri Akışları &gt; Web</div>
          </div>
          <div className="field">
            <label>API secret</label>
            <input className="input" type="password" value={ga4.api_secret} placeholder="••••••••"
              onChange={(e) => setGa4({ ...ga4, api_secret: e.target.value })} />
            <div className="hint">Aynı sayfada "API secret üret". Ölçüm için zorunlu.</div>
          </div>
          <div className="field">
            <label>GA4 property ID</label>
            <input className="input" value={ga4.property_id} placeholder="123456789"
              onChange={(e) => setGa4({ ...ga4, property_id: e.target.value })} />
            <div className="hint">Raporlar ve otomatik kurulum için gerekir.</div>
          </div>
          <div className="field">
            <label>Mod</label>
            <label className="check">
              <input type="checkbox" checked={ga4.server_side !== false}
                onChange={(e) => setGa4({ ...ga4, server_side: e.target.checked })} />
              Sunucu taraflı gönderim (önerilir)
            </label>
          </div>
        </div>
        <div className="row">
          <button className="btn btn-primary" type="button" onClick={saveGa4} disabled={busy === "ga4"}>Kaydet</button>
          <button className="btn" type="button" onClick={ga4Test} disabled={busy === "ga4_test"}>Bağlantı testi (olay gönder)</button>
          <button className="btn" type="button" onClick={ga4Setup} disabled={busy === "ga4_setup"}>Custom dimension + key event oluştur</button>
        </div>
        <p className="small muted" style={{ marginTop: 10 }}>
          API secret olmadan sunucu modu kapalı kalır; olaylar tarayıcı gtag etiketiyle gönderilir.
        </p>
      </div>

      {/* ---------- integrations ---------- */}
      {PROVIDERS.map((p) => {
        const form = forms[p.key] || {};
        return (
          <div className="card card-pad" key={p.key} style={{ marginTop: 16 }}>
            <div className="card-head">
              <div>
                <h3>{p.name}</h3>
                <p className="muted small">{p.desc}</p>
              </div>
              <div className="row">
                <span className={`badge ${form.status === "connected" ? "ok" : form.status === "error" ? "bad" : ""}`}>
                  {form.status || "not_configured"}
                </span>
                <label className="check">
                  <input type="checkbox" checked={Boolean(form.enabled)}
                    onChange={(e) => setForm(p.key, "enabled", e.target.checked)} />
                  aktif
                </label>
              </div>
            </div>
            <div className="grid-2">
              <div className="field">
                <label>OAuth Client ID</label>
                <input className="input" value={form.client_id || ""} placeholder="...apps.googleusercontent.com"
                  onChange={(e) => setForm(p.key, "client_id", e.target.value)} />
              </div>
              <div className="field">
                <label>OAuth Client secret</label>
                <input className="input" type="password" value={form.client_secret || ""} placeholder={form.has_secret ? "•••• (kayıtlı)" : ""}
                  onChange={(e) => setForm(p.key, "client_secret", e.target.value)} />
              </div>
              <div className="field">
                <label>Refresh token</label>
                <input className="input" type="password" value={form.refresh_token || ""} placeholder={form.has_refresh_token ? "•••• (kayıtlı)" : "1//0e..."}
                  onChange={(e) => setForm(p.key, "refresh_token", e.target.value)} />
                <div className="hint">İzin: {p.scopes.join(", ")}</div>
              </div>
              <div className="field">
                <label>Yapılandırma (JSON)</label>
                <textarea className="input mono" rows={3} value={form.configText || "{}"}
                  onChange={(e) => setForm(p.key, "configText", e.target.value)} spellCheck={false} />
                <div className="hint">{p.configHint}</div>
              </div>
            </div>
            <div className="row">
              <button className="btn btn-primary btn-sm" type="button" onClick={() => saveIntegration(p.key)} disabled={busy === p.key}>
                Kaydet
              </button>
              <button className="btn btn-sm" type="button" onClick={() => run(p.key, () => api(`/api/admin/google/integrations/${p.key}/test`, { method: "POST" }))} disabled={busy === p.key}>
                Bağlantı testi
              </button>
              {p.key === "search_console" && (
                <button className="btn btn-sm" type="button" onClick={submitSitemap} disabled={busy === "sitemap"}>
                  Sitemap gönder
                </button>
              )}
            </div>
            {form.last_error && <p className="small" style={{ color: "var(--danger)" }}>{form.last_error}</p>}
          </div>
        );
      })}

      {/* ---------- reports ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Raporlar</h2><p>Veriler doğrudan Google API'lerinden çekilir.</p></div>
      </div>
      <div className="grid-2">
        <div className="card card-pad">
          <div className="card-head">
            <div><h3>GA4 — son 30 gün</h3></div>
            <button className="btn btn-sm" type="button" onClick={() => run("r1", async () => { setGa4Report(await api("/api/admin/google/ga4/report?days=30")); return { ok: true }; })}>
              Getir
            </button>
          </div>
          {ga4Report ? (
            <>
              <div className="mini-facts">
                <div><span>Aktif kullanıcı</span><strong>{ga4Report.totals.active_users}</strong></div>
                <div><span>Yeni kullanıcı</span><strong>{ga4Report.totals.new_users}</strong></div>
                <div><span>Oturum</span><strong>{ga4Report.totals.sessions}</strong></div>
                <div><span>Dönüşüm</span><strong>{ga4Report.totals.key_events}</strong></div>
                <div><span>Ciro</span><strong>{ga4Report.totals.revenue}</strong></div>
              </div>
              <div className="table-wrap" style={{ marginTop: 12 }}>
                <table className="tbl compact">
                  <thead><tr><th>Olay</th><th className="num">Sayı</th><th className="num">Dönüşüm</th><th className="num">Ciro</th></tr></thead>
                  <tbody>
                    {ga4Report.events.map((e, i) => (
                      <tr key={i}>
                        <td className="mono small">{e.dimensions[0]}</td>
                        <td className="num">{e.metrics[0]}</td>
                        <td className="num">{e.metrics[1]}</td>
                        <td className="num">{e.metrics[2]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : <p className="muted small">Henüz çekilmedi.</p>}
        </div>

        <div className="card card-pad">
          <div className="card-head">
            <div><h3>Search Console — son 28 gün</h3></div>
            <button className="btn btn-sm" type="button" onClick={() => run("r2", async () => { setScReport(await api("/api/admin/google/search-console/report?days=28")); return { ok: true }; })}>
              Getir
            </button>
          </div>
          {scReport ? (
            <div className="table-wrap">
              <table className="tbl compact">
                <thead><tr><th>Sorgu</th><th>Sayfa</th><th className="num">Tıklama</th><th className="num">Gösterim</th><th className="num">CTR</th><th className="num">Poz.</th></tr></thead>
                <tbody>
                  {scReport.rows.slice(0, 25).map((r, i) => (
                    <tr key={i}>
                      <td className="small">{r.keys?.[0]}</td>
                      <td className="small muted">{r.keys?.[1]}</td>
                      <td className="num">{r.clicks}</td>
                      <td className="num">{r.impressions}</td>
                      <td className="num">{r.ctr}</td>
                      <td className="num">{r.position}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="muted small">Henüz çekilmedi.</p>}
        </div>
      </div>

      {/* ---------- queue ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div>
          <h2>GA4 gönderim kuyruğu</h2>
          <p>Sunucu taraflı gönderilen olaylar ve durumları.</p>
        </div>
        <button className="btn btn-sm" type="button" onClick={loadQueue}><Icon name="refresh" size={14} /> Yenile</button>
      </div>
      {queue && (
        <>
          <div className="row" style={{ marginBottom: 10 }}>
            <span className="badge ok">iletildi: {queue.delivered}</span>
            <span className="badge warn">bekleyen: {queue.pending}</span>
            <span className={`badge ${queue.server_side ? "ok" : ""}`}>
              {queue.server_side ? "sunucu modu aktif" : "tarayıcı modu"}
            </span>
          </div>
          <div className="card table-wrap">
            <table className="tbl compact">
              <thead><tr><th>Zaman</th><th>Olay</th><th>Kaynak</th><th>Değer</th><th>Durum</th></tr></thead>
              <tbody>
                {queue.events.map((e) => (
                  <tr key={e.id}>
                    <td className="small">{e.created_at ? new Date(e.created_at).toLocaleString("tr-TR") : "—"}</td>
                    <td className="mono small">{e.name}</td>
                    <td className="small">{e.source}</td>
                    <td className="num small">{e.value != null ? `${e.value} ${e.currency ?? ""}` : "—"}</td>
                    <td>{e.delivered ? <span className="badge ok">iletildi</span> : <span className="badge warn">bekliyor</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
