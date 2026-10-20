import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ACTIVE_STATUSES, api, fmtCost, fmtDate, fmtTokens, shortId, TEMPLATES } from "../api.js";
import Icon from "../icons.jsx";

const TILE_COLORS = [
  "linear-gradient(135deg,#6366f1,#8b5cf6)",
  "linear-gradient(135deg,#0d9488,#14b8a6)",
  "linear-gradient(135deg,#f59e0b,#f97316)",
  "linear-gradient(135deg,#ec4899,#f43f5e)",
  "linear-gradient(135deg,#3b82f6,#06b6d4)",
  "linear-gradient(135deg,#8b5cf6,#d946ef)",
];

function statusBadge(s) {
  if (s === "completed") return <span className="badge ok">tamamlandı</span>;
  if (s === "failed") return <span className="badge bad">hata</span>;
  if (ACTIVE_STATUSES.includes(s)) return <span className="badge run">{s}</span>;
  return <span className="badge">{s}</span>;
}

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [runs, setRuns] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    Promise.all([api("/api/projects"), api("/api/runs")])
      .then(([p, r]) => {
        setProjects(p);
        setRuns(r);
      })
      .catch((e) => setErr(e.message));
  }, []);

  const active = runs.filter((r) => ACTIVE_STATUSES.includes(r.status)).length;
  const done = runs.filter((r) => r.status === "completed").length;
  const tokens = runs.reduce((a, r) => a + (r.tokens_used || 0), 0);
  const cost = runs.reduce((a, r) => a + Number(r.cost_usd || 0), 0);
  const recent = runs.slice(0, 6);

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Çalışma alanına hoş geldiniz</h2>
          <p>Simülasyonlarınız, projeleriniz ve kullanımınız tek ekranda.</p>
        </div>
        <Link className="btn btn-primary" to="/app/projects/new">
          <Icon name="plus" size={16} /> Yeni Simülasyon
        </Link>
      </div>

      {err && <p className="error">{err}</p>}

      <div className="stat-grid">
        <div className="card stat card-hover">
          <span className="stat-icon"><Icon name="folder" size={18} /></span>
          <div className="stat-label">Projeler</div>
          <div className="stat-value">{projects.length}</div>
          <div className="stat-sub">araştırma alanı</div>
        </div>
        <div className="card stat card-hover">
          <span className="stat-icon" style={{ background: "#ecfdf5", color: "#047857" }}>
            <Icon name="activity" size={18} />
          </span>
          <div className="stat-label">Simülasyon</div>
          <div className="stat-value">{runs.length}</div>
          <div className="stat-sub">{active} çalışıyor · {done} tamamlandı</div>
        </div>
        <div className="card stat card-hover">
          <span className="stat-icon" style={{ background: "#fffbeb", color: "#b45309" }}>
            <Icon name="chart" size={18} />
          </span>
          <div className="stat-label">Token</div>
          <div className="stat-value">{fmtTokens(tokens)}</div>
          <div className="stat-sub">toplam kullanılan</div>
        </div>
        <div className="card stat card-hover">
          <span className="stat-icon" style={{ background: "#fdf2f8", color: "#be185d" }}>
            <Icon name="card" size={18} />
          </span>
          <div className="stat-label">Maliyet</div>
          <div className="stat-value">{fmtCost(cost)}</div>
          <div className="stat-sub">kümülatif LLM maliyeti</div>
        </div>
      </div>

      <div className="card">
        <div className="card-pad row-between" style={{ paddingBottom: 10 }}>
          <div>
            <h3>Hızlı başlangıç</h3>
            <p className="small muted">Bir şablon seçin, 3 adımda simülasyonunuzu oluşturun.</p>
          </div>
        </div>
        <div style={{ padding: "4px 20px 22px" }}>
          <div className="quick-grid">
            {TEMPLATES.map((t, i) => (
              <Link className="quick-card" to={`/app/projects/new?tpl=${t.key}`} key={t.key}>
                <span className="q-icon" style={{ background: TILE_COLORS[i % TILE_COLORS.length] }}>
                  <Icon name="box" size={17} />
                </span>
                <span>
                  <h4>{t.name}</h4>
                  <p>{t.desc}</p>
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-pad row-between" style={{ paddingBottom: 10 }}>
          <h3>Son simülasyonlar</h3>
          <Link className="small" to="/app/runs">tümü →</Link>
        </div>
        {recent.length === 0 ? (
          <div style={{ padding: "8px 20px 24px" }}>
            <div className="empty">
              <span className="empty-icon"><Icon name="play" size={22} /></span>
              <h3>Henüz simülasyon yok</h3>
              <p>Bir proje oluşturun, şablon seçin ve topluluk simülasyonunuzu başlatın.</p>
              <Link className="btn btn-primary" to="/app/projects/new">
                <Icon name="plus" size={15} /> İlk simülasyonu oluştur
              </Link>
            </div>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Koşu</th><th>Proje</th><th>Durum</th><th className="num">Tur</th>
                  <th className="num">Token</th><th className="num">Maliyet</th><th>Başlangıç</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r) => (
                  <tr key={r.id}>
                    <td><Link className="mono" to={`/app/runs/${r.id}`}>{shortId(r.id)}</Link></td>
                    <td style={{ fontWeight: 600 }}>{r.project_name ?? "—"}</td>
                    <td>{statusBadge(r.status)}</td>
                    <td className="num">{r.current_round ?? 0}</td>
                    <td className="num">{fmtTokens(r.tokens_used)}</td>
                    <td className="num">{fmtCost(r.cost_usd)}</td>
                    <td className="muted small">{fmtDate(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
