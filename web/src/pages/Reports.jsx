import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, downloadReport, fmtCost, fmtDate, fmtTokens } from "../api.js";
import Icon from "../icons.jsx";

export default function Reports() {
  const [runs, setRuns] = useState([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    api("/api/runs")
      .then((rows) => setRuns(rows.filter((r) => r.report_ready)))
      .catch((e) => setErr(e.message));
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLocaleLowerCase("tr-TR");
    if (!needle) return runs;
    return runs.filter((r) =>
      [r.project_name, r.id, r.template_key]
        .filter(Boolean)
        .some((v) => String(v).toLocaleLowerCase("tr-TR").includes(needle)),
    );
  }, [runs, q]);

  async function download(run, format) {
    setBusy(`${run.id}:${format}`);
    setErr(null);
    try {
      await downloadReport(run.id, format);
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  const totalTokens = runs.reduce((sum, r) => sum + Number(r.tokens_used || 0), 0);
  const totalCost = runs.reduce((sum, r) => sum + Number(r.cost_usd || 0), 0);

  return (
    <>
      <div className="page-head">
        <div><h2>Raporlar</h2><p>Tamamlanan simülasyonların kaynakçalı analiz çıktıları. Her rapor kalıcı simülasyon ibaresi taşır.</p></div>
        <Link className="btn btn-primary" to="/app/projects/new"><Icon name="plus" size={15} /> Yeni simülasyon</Link>
      </div>

      <div className="notice"><Icon name="bell" size={15} /><span>Çıktılar gerçek anket veya kamuoyu ölçümü değildir; yalnızca simülasyon ürünüdür.</span></div>

      {err && <p className="error">{err}</p>}

      <div className="stat-grid" style={{ marginBottom: 4 }}>
        <div className="card stat"><div className="stat-label"><Icon name="doc" size={15} /> Rapor</div><div className="stat-value">{runs.length}</div><div className="stat-sub">indirilebilir PDF/Markdown</div></div>
        <div className="card stat"><div className="stat-label"><Icon name="chart" size={15} /> Toplam token</div><div className="stat-value">{fmtTokens(totalTokens)}</div><div className="stat-sub">rapor üretiminde tüketilen</div></div>
        <div className="card stat"><div className="stat-label"><Icon name="card" size={15} /> Toplam maliyet</div><div className="stat-value">{fmtCost(totalCost)}</div><div className="stat-sub">model maliyeti (satış fiyatı değil)</div></div>
        <div className="card stat"><div className="stat-label"><Icon name="activity" size={15} /> Son rapor</div><div className="stat-value" style={{ fontSize: 18 }}>{runs[0] ? fmtDate(runs[0].finished_at || runs[0].created_at) : "—"}</div><div className="stat-sub">tamamlanma zamanı</div></div>
      </div>

      <div className="page-head" style={{ marginTop: 18 }}>
        <div><h3 style={{ fontSize: 17 }}>Rapor kütüphanesi</h3></div>
        <input className="input" placeholder="Proje adı veya run ID ara" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 260 }} />
      </div>

      <div className="card table-wrap">
        <table className="tbl">
          <thead>
            <tr><th>Proje</th><th>Run</th><th>Durum</th><th className="num">Token</th><th className="num">Maliyet</th><th>Tamamlandı</th><th>İşlem</th></tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id}>
                <td><Link to={`/app/runs/${r.id}`} style={{ fontWeight: 620 }}>{r.project_name || "—"}</Link></td>
                <td className="mono small">{String(r.id).slice(0, 8)}</td>
                <td><span className="badge ok">hazır</span></td>
                <td className="num">{fmtTokens(r.tokens_used)}</td>
                <td className="num">{fmtCost(r.cost_usd)}</td>
                <td className="small muted">{fmtDate(r.finished_at || r.created_at)}</td>
                <td className="num">
                  <button className="btn btn-sm" type="button" disabled={busy === `${r.id}:pdf`} onClick={() => download(r, "pdf")}>
                    {busy === `${r.id}:pdf` ? "…" : "PDF"}
                  </button>{" "}
                  <button className="btn btn-sm" type="button" disabled={busy === `${r.id}:md`} onClick={() => download(r, "md")}>
                    {busy === `${r.id}:md` ? "…" : "MD"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && !err && (
          <div className="empty">
            <span className="empty-icon"><Icon name="doc" size={22} /></span>
            <h3>{runs.length === 0 ? "Henüz rapor yok" : "Eşleşen rapor yok"}</h3>
            <p>{runs.length === 0 ? "İlk simülasyonunuz tamamlandığında rapor burada listelenir." : "Farklı bir arama deneyin."}</p>
            {runs.length === 0 && <Link className="btn btn-primary" to="/app/projects/new"><Icon name="play" size={15} /> Simülasyon oluştur</Link>}
          </div>
        )}
      </div>
    </>
  );
}
