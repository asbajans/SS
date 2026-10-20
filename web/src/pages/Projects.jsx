import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmtDate, TEMPLATES } from "../api.js";
import Icon from "../icons.jsx";

const TPL_NAME = Object.fromEntries(TEMPLATES.map((t) => [t.key, t.name]));

function statusBadge(s) {
  if (s === "completed") return <span className="badge ok">tamamlandı</span>;
  if (s === "failed") return <span className="badge bad">hata</span>;
  if (s === "active" || s === "running") return <span className="badge run">{s}</span>;
  return <span className="badge">{s ?? "draft"}</span>;
}

export default function Projects() {
  const [projects, setProjects] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api("/api/projects").then(setProjects).catch((e) => setErr(e.message));
  }, []);

  return (
    <>
      <div className="page-head">
        <div><h2>Projeler</h2><p>Her proje bir araştırma konusu, şablon ve simülasyon yapılandırmasıdır.</p></div>
        <Link className="btn btn-primary" to="/app/projects/new"><Icon name="plus" size={16} /> Yeni Simülasyon</Link>
      </div>

      {err && <p className="error">{err}</p>}

      {projects === null ? (
        <div className="shell-loading" style={{ minHeight: 200 }}><div className="spinner" /></div>
      ) : projects.length === 0 ? (
        <div className="empty"><span className="empty-icon"><Icon name="folder" size={22} /></span>
          <h3>Projeniz yok</h3>
          <p>Pazar araştırması, kamuoyu analizi, fiyat testi ve daha fazlası için hazır şablonlarla ilk projenizi oluşturun.</p>
          <Link className="btn btn-primary" to="/app/projects/new"><Icon name="plus" size={15} /> Projeyi oluştur</Link>
        </div>
      ) : (
        <div className="card table-wrap">
          <table className="tbl">
            <thead><tr><th>Proje</th><th>Şablon</th><th>Durum</th><th>Dil</th><th>Oluşturma</th><th>İşlem</th></tr></thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontWeight: 620 }}>{p.name}</td>
                  <td>{TPL_NAME[p.template_key] ?? p.template_key}</td>
                  <td>{statusBadge(p.status)}</td>
                  <td className="muted">{(p.language ?? "tr").toUpperCase()}</td>
                  <td className="muted small">{fmtDate(p.created_at)}</td>
                  <td className="num"><Link className="btn btn-sm" to={`/app/projects/${p.id}`}>Aç</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
