import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ACTIVE_STATUSES, api, fmtCost, fmtDate, fmtTokens, PROFILES, shortId, TEMPLATES, uploadDocument } from "../api.js";
import Icon from "../icons.jsx";

const TABS = ["Genel Bakış", "Simülasyonlar", "Belgeler", "Ontoloji & Ajanlar", "Rapor"];

function statusBadge(s) {
  if (s === "completed") return <span className="badge ok">tamamlandı</span>;
  if (s === "failed") return <span className="badge bad">hata</span>;
  if (ACTIVE_STATUSES.includes(s)) return <span className="badge run">{s}</span>;
  return <span className="badge">{s}</span>;
}

function profileLabel(cfg) {
  if (!cfg) return "—";
  const hit = PROFILES.find((p) => p.agents_n === cfg.agents_n && p.rounds === cfg.rounds);
  return hit ? hit.name : `Özel (${cfg.agents_n ?? "?"} ajan / ${cfg.rounds ?? "?"} tur)`;
}

export default function ProjectDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [project, setProject] = useState(null);
  const [runs, setRuns] = useState([]);
  const [tab, setTab] = useState(0);
  const [err, setErr] = useState(null);
  const [starting, setStarting] = useState(false);
  const [docs, setDocs] = useState([]);
  const [agents, setAgents] = useState([]);
  const [ontology, setOntology] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [docMsg, setDocMsg] = useState(null);

  const load = useCallback(() => {
    Promise.all([
      api("/api/projects"),
      api("/api/runs"),
      api(`/api/projects/${id}/documents`),
      api(`/api/projects/${id}/agents`),
      api(`/api/projects/${id}/ontology`),
    ])
      .then(([ps, rs, ds, ags, onto]) => {
        const p = ps.find((x) => x.id === id);
        if (!p) { setErr("Proje bulunamadı"); return; }
        setProject(p); setRuns(rs.filter((r) => r.project_id === id));
        setDocs(ds); setAgents(ags); setOntology(onto);
      }).catch((e) => setErr(e.message));
  }, [id]);

  useEffect(load, [load]);

  const hasActive = useMemo(() => runs.some((r) => ACTIVE_STATUSES.includes(r.status)), [runs]);

  useEffect(() => {
    if (!hasActive) return undefined;
    const t = setInterval(load, 5000); return () => clearInterval(t);
  }, [hasActive, load]);

  async function startRun() {
    setStarting(true); setErr(null);
    try {
      const r = await api(`/api/projects/${id}/runs`, { method: "POST" });
      nav(`/app/runs/${r.run_id}`);
    } catch (e) { setErr(e.message); setStarting(false); }
  }

  async function onUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true); setDocMsg(null); setErr(null);
    try {
      const d = await uploadDocument(id, file);
      setDocMsg(`${d.filename} yüklendi; metin çıkarma ve gömme kuyruğa alındı.`);
      load();
      setTimeout(load, 6000);
    } catch (ex) { setErr(ex.message); }
    setUploading(false);
  }

  async function removeDoc(docId) {
    try {
      await api(`/api/documents/${docId}`, { method: "DELETE" });
      load();
    } catch (ex) { setErr(ex.message); }
  }

  if (err && !project) {
    return (<><p className="error">{err}</p><Link className="btn" to="/app/projects">← Projelere dön</Link></>);
  }
  if (!project) return <div className="shell-loading" style={{ minHeight: 200 }}><div className="spinner" /></div>;

  const tpl = TEMPLATES.find((t) => t.key === project.template_key);
  const tokens = runs.reduce((a, r) => a + (r.tokens_used || 0), 0);
  const cost = runs.reduce((a, r) => a + Number(r.cost_usd || 0), 0);
  const lastRun = runs[0];

  return (
    <>
      <div className="detail-head">
        <div>
          <span className="crumb"><Link to="/app/projects">Projeler</Link><Icon name="chevron" size={13} /> {project.name}</span>
          <h2>{project.name}</h2>
          <div className="row" style={{ marginTop: 8 }}>
            {statusBadge(project.status)}
            <span className="badge no-dot">{tpl?.name ?? project.template_key}</span>
            <span className="badge no-dot">{(project.language ?? "tr").toUpperCase()}</span>
          </div>
        </div>
        <button className="btn btn-primary" type="button" onClick={startRun} disabled={starting}>
          <Icon name="play" size={15} /> {starting ? "Kuyruğa alınıyor…" : "Simülasyon Başlat"}
        </button>
      </div>

      {err && <p className="error">{err}</p>}

      <div className="tabs">
        {TABS.map((t, i) => (
          <button key={t} type="button" className={`tab${tab === i ? " active" : ""}`} onClick={() => setTab(i)}>{t}</button>
        ))}
      </div>

      {tab === 0 && (
        <div className="grid-2">
          <div className="card card-pad stack">
            <h3>Proje bilgileri</h3>
            <dl className="kv">
              <dt>Şablon</dt><dd>{tpl?.name ?? project.template_key}</dd>
              <dt>Açıklama</dt><dd className="text-2">{tpl?.desc ?? "—"}</dd>
              <dt>Dil</dt><dd>{(project.language ?? "tr").toUpperCase()}</dd>
              <dt>Profil</dt><dd>{profileLabel(project.sim_config)}</dd>
              <dt>Oluşturma</dt><dd>{fmtDate(project.created_at)}</dd>
              <dt>Proje ID</dt><dd className="mono small">{project.id}</dd>
            </dl>
          </div>
          <div className="card card-pad stack">
            <h3>Kullanım</h3>
            <div className="grid-2">
              <div className="card stat" style={{ boxShadow: "none" }}>
                <div className="stat-label">Simülasyon</div><div className="stat-value" style={{ fontSize: 22 }}>{runs.length}</div>
              </div>
              <div className="card stat" style={{ boxShadow: "none" }}>
                <div className="stat-label">Token</div><div className="stat-value" style={{ fontSize: 22 }}>{fmtTokens(tokens)}</div>
              </div>
            </div>
            <dl className="kv">
              <dt>Maliyet</dt><dd>{fmtCost(cost)}</dd>
              <dt>Son koşu</dt><dd>{lastRun ? (<Link className="mono" to={`/app/runs/${lastRun.id}`}>{shortId(lastRun.id)} · {lastRun.status}</Link>) : "—"}</dd>
            </dl>
            <div className="notice"><Icon name="bell" size={15} /><span>Bu projenin tüm çıktıları simülasyon ürünüdür; saha araştırması değildir.</span></div>
          </div>
        </div>
      )}

      {tab === 1 && (
        <div className="card">
          {runs.length === 0 ? (
            <div style={{ padding: 20 }}>
              <div className="empty"><span className="empty-icon"><Icon name="play" size={22} /></span>
                <h3>Simülasyon çalıştırılmadı</h3>
                <p>Sağ üstteki “Simülasyon Başlat” ile bu projede ilk koşuyu oluşturun.</p>
                <button className="btn btn-primary" type="button" onClick={startRun} disabled={starting}><Icon name="play" size={15} /> Başlat</button>
              </div>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr><th>Koşu</th><th>Durum</th><th className="num">Tur</th><th className="num">Token</th><th className="num">Maliyet</th><th>Başlangıç</th></tr></thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td><Link className="mono" to={`/app/runs/${r.id}`}>{shortId(r.id)}</Link></td>
                      <td>{statusBadge(r.status)}</td>
                      <td className="num">{r.current_round ?? 0}</td><td className="num">{fmtTokens(r.tokens_used)}</td><td className="num">{fmtCost(r.cost_usd)}</td><td className="muted small">{fmtDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 2 && (
        <div className="card card-pad stack">
          <div className="upload-row">
            <label className="btn btn-primary" htmlFor="docfile">
              <Icon name="upload" size={16} /> {uploading ? "Yükleniyor…" : "Belge Yükle"}
            </label>
            <input id="docfile" type="file" accept=".txt,.md,.pdf" onChange={onUpload} disabled={uploading} />
            <span className="small muted">PDF / TXT / MD · en fazla 20 MB</span>
          </div>
          {docMsg && <p className="small" style={{ color: "var(--ok, #047857)" }}>{docMsg}</p>}
          {docs.length === 0 ? (
            <div className="empty"><span className="empty-icon"><Icon name="doc" size={22} /></span>
              <h3>Kaynak belge yok</h3>
              <p>Belge eklemezseniz simülasyon proje adı ve şablon açıklamasıyla başlar; kaynak eklemek çıktıları zenginleştirir.</p>
            </div>
          ) : (
            <div>
              {docs.map((d) => (
                <div className="doc-row" key={d.id}>
                  <div>
                    <div style={{ fontWeight: 650 }}>{d.filename}</div>
                    <div className="small muted">{(d.size / 1024).toFixed(1)} KB · {d.chunks ? `${d.chunks} parça` : "işleniyor…"}</div>
                  </div>
                  <button className="btn" type="button" onClick={() => removeDoc(d.id)}>Sil</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 3 && (
        <div className="stack">
          {ontology?.exists && (
            <div className="card card-pad">
              <h3 style={{ marginBottom: 10 }}>Ontoloji</h3>
              <div className="agent-attrs">
                {(ontology.entity_types?.items ?? []).map((x) => <span className="attr-chip" key={`e-${x}`}>{x}</span>)}
                {(ontology.relation_types?.items ?? []).map((x) => <span className="attr-chip" key={`r-${x}`} style={{ background: "#ecfeff", color: "#0e7490" }}>{x}</span>)}
              </div>
              {ontology.seed_summary && <p className="small muted" style={{ marginTop: 10 }}>{ontology.seed_summary}</p>}
            </div>
          )}
          {agents.length === 0 ? (
            <div className="empty"><span className="empty-icon"><Icon name="users" size={22} /></span>
              <h3>Ontoloji ve ajanlar henüz üretilmedi</h3>
              <p>Simülasyon başlatıldığında sistem belgelerden ontoloji çıkarır ve persona popülasyonu oluşturur; bu sekmede ajan kartlarını göreceksiniz.</p>
            </div>
          ) : (
            <div className="card card-pad">
              <h3 style={{ marginBottom: 12 }}>Ajanlar ({agents.length})</h3>
              <div className="agent-grid">
                {agents.map((a) => (
                  <div className="agent-card" key={a.id}>
                    <h4>{a.name}</h4>
                    <p>{a.bio}</p>
                    <div className="agent-attrs">
                      {Object.entries(a.attributes ?? {}).slice(0, 6).map(([k, v]) => (
                        <span className="attr-chip" key={k}>{k}: {String(v)}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 4 && (
        <div className="stack">
          <div className="notice"><Icon name="bell" size={15} /><span>Raporlar simülasyon çıktısıdır; gerçek anket/kamuoyu ölçümü olarak kullanılamaz. Kaynakça ve olay izleri raporda yer alır.</span></div>
          <div className="empty"><span className="empty-icon"><Icon name="doc" size={22} /></span>
            <h3>Rapor henüz hazır değil</h3>
            <p>Tamamlanan bir simülasyondan sonra Markdown rapor indirilebilir hale gelecek.</p>
          </div>
        </div>
      )}
    </>
  );
}
