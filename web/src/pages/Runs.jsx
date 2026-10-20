import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ACTIVE_STATUSES, api, fmtCost, fmtDate, fmtTokens, shortId } from "../api.js";
import Icon from "../icons.jsx";

function statusBadge(s) {
  if (s === "completed") return <span className="badge ok">tamamlandı</span>;
  if (s === "failed") return <span className="badge bad">hata</span>;
  if (ACTIVE_STATUSES.includes(s)) return <span className="badge run">{s}</span>;
  return <span className="badge">{s}</span>;
}

export default function Runs() {
  const [runs, setRuns] = useState(null);
  const [err, setErr] = useState(null);

  const load = () => api("/api/runs").then(setRuns).catch((e) => setErr(e.message));

  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!runs || !runs.some((r) => ACTIVE_STATUSES.includes(r.status))) return undefined;
    const t = setInterval(load, 5000); return () => clearInterval(t);
  }, [runs]);

  return (
    <>
      <div className="page-head">
        <div><h2>Simülasyonlar</h2><p>Tüm projelerinizdeki koşular ve canlı durumları.</p></div>
        <Link className="btn btn-primary" to="/app/projects/new"><Icon name="plus" size={16} /> Yeni Simülasyon</Link>
      </div>

      {err && <p className="error">{err}</p>}

      {runs === null ? (
        <div className="shell-loading" style={{ minHeight: 200 }}><div className="spinner" /></div>
      ) : runs.length === 0 ? (
        <div className="empty"><span className="empty-icon"><Icon name="activity" size={22} /></span>
          <h3>Simülasyon kaydı yok</h3>
          <p>Bir projeden simülasyon başlattığınızda koşular burada listelenir.</p>
          <Link className="btn btn-primary" to="/app/projects/new">İlk simülasyonu oluştur</Link>
        </div>
      ) : (
        <div className="card table-wrap">
          <table className="tbl">
            <thead><tr><th>Koşu</th><th>Proje</th><th>Durum</th><th className="num">Tur</th><th className="num">Token</th><th className="num">Maliyet</th><th>Başlangıç</th></tr></thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td><Link className="mono" to={`/app/runs/${r.id}`}>{shortId(r.id)}</Link></td>
                  <td>{r.project_name ?? "—"}</td><td>{statusBadge(r.status)}</td>
                  <td className="num">{r.current_round ?? 0}</td><td className="num">{fmtTokens(r.tokens_used)}</td><td className="num">{fmtCost(r.cost_usd)}</td><td className="muted small">{fmtDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
