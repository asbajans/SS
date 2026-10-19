import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ACTIVE_STATUSES, api, fmtCost, fmtDate, fmtTokens, STAGES, stageIndex } from "../api.js";
import Icon from "../icons.jsx";

export default function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [err, setErr] = useState(null);

  const load = useCallback(
    () => api(`/api/runs/${id}`).then(setRun).catch((e) => setErr(e.message)),
    [id]
  );

  useEffect(() => {
    load();
  }, [load]);

  const active = run && ACTIVE_STATUSES.includes(run.status);

  useEffect(() => {
    if (!active) return undefined;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [active, load]);

  if (err && !run) {
    return (
      <>
        <p className="error">{err}</p>
        <Link className="btn" to="/app/runs">← Simülasyonlara dön</Link>
      </>
    );
  }
  if (!run) {
    return <div className="shell-loading" style={{ minHeight: 220 }}><div className="spinner" /></div>;
  }

  const idx = stageIndex(run.status);
  const failed = run.status === "failed";

  return (
    <>
      <div className="detail-head">
        <div>
          <span className="crumb">
            <Link to="/app/runs">Simülasyonlar</Link>
            <Icon name="chevron" size={13} /> {String(run.id).slice(0, 8)}
          </span>
          <h2>Simülasyon <span className="mono" style={{ fontSize: 18 }}>{String(run.id).slice(0, 8)}</span></h2>
          <div className="row" style={{ marginTop: 8 }}>
            {failed ? (
              <span className="badge bad">hata</span>
            ) : run.status === "completed" ? (
              <span className="badge ok">tamamlandı</span>
            ) : (
              <span className="badge run">{run.status}</span>
            )}
            {run.project_name && (
              <Link className="badge no-dot" to={`/app/projects/${run.project_id}`}>
                {run.project_name}
              </Link>
            )}
            {run.template_key && <span className="badge no-dot">{run.template_key}</span>}
          </div>
        </div>
        {run.report_object_key && (
          <button className="btn" type="button" disabled title="Rapor indirme F3'te geliyor">
            <Icon name="doc" size={15} /> Raporu indir
          </button>
        )}
      </div>

      <div className="stat-grid">
        <div className="card stat">
          <div className="stat-label">Tur</div>
          <div className="stat-value" style={{ fontSize: 22 }}>{run.current_round ?? 0}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Token</div>
          <div className="stat-value" style={{ fontSize: 22 }}>{fmtTokens(run.tokens_used)}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Maliyet</div>
          <div className="stat-value" style={{ fontSize: 22 }}>{fmtCost(run.cost_usd)}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Başlangıç</div>
          <div className="stat-value" style={{ fontSize: 15, marginTop: 10 }}>{fmtDate(run.created_at)}</div>
        </div>
      </div>

      {failed && run.error && <p className="error">{run.error}</p>}

      <div className="card card-pad">
        <h3 style={{ marginBottom: 16 }}>İşlem hattı</h3>
        <div className="stage-list">
          {STAGES.map((s, i) => {
            let cls = "stage";
            if (failed && i === idx) cls += " failed";
            else if (run.status === "completed" || i < idx) cls += " done";
            else if (i === idx) cls += " current";
            return (
              <div className={cls} key={s.key}>
                <span className="s-dot">
                  {cls.includes("done") ? <Icon name="check" size={13} /> : i + 1}
                </span>
                <div className="s-body">
                  <div className="s-label">{s.label}</div>
                  <div className="s-sub">
                    {cls.includes("done")
                      ? "tamamlandı"
                      : cls.includes("current")
                        ? failed
                          ? "bu adımda hata oluştu"
                          : "işleniyor…"
                        : cls.includes("failed")
                          ? "hata"
                          : "bekliyor"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="notice">
        <Icon name="bell" size={15} />
        <span>
          Bu koşunun tüm olayları ve raporu simülasyon ürünüdür; olay akışı (SSE) ve
          rapor görüntüleme sonraki fazlarda bu sayfaya bağlanır.
        </span>
      </div>
    </>
  );
}
