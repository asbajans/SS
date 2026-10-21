import { useEffect, useState } from "react";

import { api, fmtDate } from "../api.js";
import Icon from "../icons.jsx";

const API_BASE = import.meta.env.VITE_API_URL || "https://api.socialsimulator.com.tr";

const ENDPOINTS = [
  ["GET", "/api/v1/me", "Anahtarın sahibini ve planı döner"],
  ["GET", "/api/v1/templates", "Aktif şablonları listeler"],
  ["GET", "/api/v1/projects", "Projeleri listeler"],
  ["POST", "/api/v1/projects", "Yeni proje oluşturur"],
  ["POST", "/api/v1/projects/{id}/runs", "Simülasyonu kuyruğa alır"],
  ["GET", "/api/v1/runs", "Son 100 simülasyonu listeler"],
  ["GET", "/api/v1/runs/{id}", "Durum ve rapor bilgisini döner"],
  ["GET", "/api/v1/runs/{id}/insights", "Görüş dağılımı, gerekçeler ve yorumları döner"],
  ["GET", "/api/v1/runs/{id}/report/download", "PDF veya Markdown indirir"],
];

const CURL = `curl -X POST ${API_BASE}/api/v1/projects \\
  -H "X-API-Key: ss_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{"name":"API testi","template_key":"market_research","language":"tr","sim_config":{"agents_n":80,"rounds":24}}'`;

export default function ApiAccess() {
  const [keys, setKeys] = useState([]);
  const [hooks, setHooks] = useState([]);
  const [newKey, setNewKey] = useState(null);
  const [newSecret, setNewSecret] = useState(null);
  const [keyName, setKeyName] = useState("");
  const [hookUrl, setHookUrl] = useState("");
  const [hookEvents, setHookEvents] = useState(["run.completed", "run.failed"]);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(null);

  async function load() {
    const [k, h] = await Promise.all([api("/api/api-keys"), api("/api/webhooks")]);
    setKeys(k);
    setHooks(h);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function createKey() {
    setBusy(true);
    setErr(null);
    try {
      const data = await api("/api/api-keys", {
        method: "POST",
        body: JSON.stringify({ name: keyName || "default" }),
      });
      setNewKey(data);
      setKeyName("");
      await load();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(false);
  }

  async function revokeKey(key) {
    if (!window.confirm(`"${key.name}" anahtarı iptal edilsin mi? Bu işlem geri alınamaz.`)) return;
    setErr(null);
    try {
      await api(`/api/api-keys/${key.id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function createHook() {
    setBusy(true);
    setErr(null);
    try {
      const data = await api("/api/webhooks", {
        method: "POST",
        body: JSON.stringify({ url: hookUrl, events: hookEvents }),
      });
      setNewSecret(data);
      setHookUrl("");
      await load();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(false);
  }

  async function toggleHook(hook) {
    setErr(null);
    try {
      await api(`/api/webhooks/${hook.id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !hook.active }),
      });
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function deleteHook(hook) {
    if (!window.confirm("Webhook silinsin mi?")) return;
    setErr(null);
    try {
      await api(`/api/webhooks/${hook.id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }

  function toggleEvent(event) {
    setHookEvents((current) =>
      current.includes(event) ? current.filter((e) => e !== event) : [...current, event],
    );
  }

  async function copy(text, id) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      setTimeout(() => setCopied(null), 1600);
    } catch {
      setErr("Panoya kopyalanamadı");
    }
  }

  return (
    <>
      <div className="page-head">
        <div><h2>API & Entegrasyon</h2><p>Sosyal medya araçlarınızı ve kendi uygulamalarınızı simülasyon hattına bağlayın.</p></div>
        <a className="btn" href="#api-docs"><Icon name="doc" size={15} /> Dokümantasyon</a>
      </div>

      <div className="notice"><Icon name="shield" size={15} /><span>API anahtarları plandaki ajan/tur limitlerine ve token bütçesine tabidir. Anahtar yalnızca oluşturulduğu anda gösterilir.</span></div>
      {err && <p className="error">{err}</p>}

      <div className="api-grid">
        <div className="card">
          <div className="card-head">
            <div><h3>API anahtarları</h3><p className="muted small">Sunucuda yalnızca SHA-256 özeti saklanır.</p></div>
            <span className="badge">{keys.filter((k) => !k.revoked).length} aktif</span>
          </div>

          {newKey && (
            <div className="secret-box">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <b>Yeni anahtar — şimdi kopyalayın</b>
                <button className="btn btn-sm" type="button" onClick={() => setNewKey(null)}><Icon name="x" size={13} /></button>
              </div>
              <code>{newKey.key}</code>
              <button className="btn btn-primary btn-sm" type="button" onClick={() => copy(newKey.key, "new-key")}>
                <Icon name="box" size={14} /> {copied === "new-key" ? "Kopyalandı" : "Kopyala"}
              </button>
            </div>
          )}

          <div className="row" style={{ marginBottom: 14 }}>
            <input className="input" placeholder="Anahtar adı (ör. n8n, sosyal-medya-bot)" value={keyName} maxLength={120} onChange={(e) => setKeyName(e.target.value)} />
            <button className="btn btn-primary" type="button" disabled={busy} onClick={createKey}><Icon name="plus" size={15} /> Anahtar oluştur</button>
          </div>

          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>Ad</th><th>Önek</th><th>Son kullanım</th><th>Durum</th><th></th></tr></thead>
              <tbody>
                {keys.map((k) => (
                  <tr key={k.id}>
                    <td style={{ fontWeight: 620 }}>{k.name}</td>
                    <td className="mono small">{k.prefix}…</td>
                    <td className="small muted">{k.last_used_at ? fmtDate(k.last_used_at) : "—"}</td>
                    <td>{k.revoked ? <span className="badge">iptal</span> : <span className="badge ok">aktif</span>}</td>
                    <td className="num">{!k.revoked && <button className="btn btn-sm btn-danger" type="button" onClick={() => revokeKey(k)}>İptal</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {keys.length === 0 && <div className="empty"><span className="empty-icon"><Icon name="box" size={22} /></span><h3>Henüz anahtar yok</h3><p>İlk API anahtarınızı oluşturarak başlayın.</p></div>}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div><h3>Webhook'lar</h3><p className="muted small">Simülasyon bitince imzalı HTTPS bildirimi.</p></div>
            <span className="badge">{hooks.filter((h) => h.active).length} aktif</span>
          </div>

          {newSecret && (
            <div className="secret-box">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <b>İmzalama sırrı — şimdi kopyalayın</b>
                <button className="btn btn-sm" type="button" onClick={() => setNewSecret(null)}><Icon name="x" size={13} /></button>
              </div>
              <code>{newSecret.secret}</code>
              <p className="small muted">İmza: <span className="mono">sha256=HMAC_SHA256(secret, raw_body)</span></p>
              <button className="btn btn-primary btn-sm" type="button" onClick={() => copy(newSecret.secret, "new-secret")}>
                <Icon name="box" size={14} /> {copied === "new-secret" ? "Kopyalandı" : "Kopyala"}
              </button>
            </div>
          )}

          <div className="stack">
            <input className="input" placeholder="https://ornek.com/webhooks/simulation" value={hookUrl} onChange={(e) => setHookUrl(e.target.value)} />
            <div className="row">
              {["run.completed", "run.failed"].map((event) => (
                <label className="check" key={event}>
                  <input type="checkbox" checked={hookEvents.includes(event)} onChange={() => toggleEvent(event)} />
                  <span className="mono small">{event}</span>
                </label>
              ))}
            </div>
            <button className="btn btn-primary" type="button" disabled={busy || !hookUrl.trim() || hookEvents.length === 0} onClick={createHook}>
              <Icon name="plus" size={15} /> Webhook ekle
            </button>
          </div>

          <div className="hook-list">
            {hooks.map((h) => (
              <div className="hook-row" key={h.id}>
                <div className="hook-main">
                  <span className="hook-url mono small">{h.url}</span>
                  <div className="hook-meta">
                    <span>{h.events.join(", ")}</span>
                    <span>{h.last_status ? `son: ${h.last_status}` : "henüz denenmedi"}</span>
                    {h.last_attempt_at && <span>{fmtDate(h.last_attempt_at)}</span>}
                  </div>
                </div>
                <div className="row">
                  <button className="btn btn-sm" type="button" onClick={() => toggleHook(h)}>{h.active ? "Duraklat" : "Aktifleştir"}</button>
                  <button className="btn btn-sm btn-danger" type="button" onClick={() => deleteHook(h)}>Sil</button>
                </div>
              </div>
            ))}
            {hooks.length === 0 && <p className="muted small" style={{ marginTop: 12 }}>Henüz webhook tanımlanmadı.</p>}
          </div>
        </div>
      </div>

      <div className="card" id="api-docs" style={{ marginTop: 18 }}>
        <div className="card-head"><div><h3>Hızlı başlangıç</h3><p className="muted small">Tüm isteklerde <span className="mono">X-API-Key</span> başlığı veya <span className="mono">Authorization: Bearer</span> kullanın.</p></div></div>
        <div className="api-docs-grid">
          <div>
            <table className="tbl">
              <thead><tr><th>Metot</th><th>Yol</th><th>Açıklama</th></tr></thead>
              <tbody>
                {ENDPOINTS.map(([method, path, desc]) => (
                  <tr key={`${method}-${path}`}>
                    <td><span className={`method method-${method.toLowerCase()}`}>{method}</span></td>
                    <td className="mono small">{path}</td>
                    <td className="small muted">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <pre className="code-block">{CURL}</pre>
            <p className="small muted">Webhook imzası <span className="mono">X-SS-Signature</span> başlığında gönderilir. Olay türü <span className="mono">X-SS-Event</span> başlığındadır.</p>
          </div>
        </div>
      </div>
    </>
  );
}
