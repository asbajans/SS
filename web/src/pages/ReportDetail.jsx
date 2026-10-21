import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, downloadReport } from "../api.js";
import Icon from "../icons.jsx";

const STANCE_META = [
  { key: "positive", label: "Olumlu", color: "#4ade80", tone: "pos" },
  { key: "negative", label: "Olumsuz", color: "#fb7185", tone: "neg" },
  { key: "neutral", label: "Nötr", color: "#94a3b8", tone: "neu" },
  { key: "undecided", label: "Kararsız", color: "#fbbf24", tone: "und" },
];

function pct(value) {
  return `${Number(value || 0).toFixed(1).replace(".0", "")}%`;
}

function SentimentBar({ summary }) {
  const percentages = summary?.percentages ?? {};
  return (
    <div className="sentiment-bar" aria-label="Görüş dağılımı">
      {STANCE_META.map((item) => {
        const value = Number(percentages[item.key] || 0);
        if (!value) return null;
        return (
          <span
            key={item.key}
            className={`sentiment-seg ${item.tone}`}
            style={{ width: `${value}%` }}
            title={`${item.label}: ${pct(value)}`}
          />
        );
      })}
    </div>
  );
}

function Donut({ summary }) {
  const percentages = summary?.percentages ?? {};
  let cursor = 0;
  const stops = STANCE_META.map((item) => {
    const value = Number(percentages[item.key] || 0);
    const start = cursor;
    cursor += value;
    return `${item.color} ${start}% ${cursor}%`;
  }).join(", ");
  const gradient = summary?.total ? `conic-gradient(${stops})` : "#e2e8f0";
  return (
    <div className="donut-wrap">
      <div className="donut" style={{ background: gradient }}>
        <div className="donut-hole">
          <strong>{summary?.total ?? 0}</strong>
          <span>katılımcı</span>
        </div>
      </div>
      <div className="donut-legend">
        {STANCE_META.map((item) => (
          <div className="legend-row" key={item.key}>
            <span className="legend-dot" style={{ background: item.color }} />
            <span>{item.label}</span>
            <strong>{summary?.[item.key] ?? 0}</strong>
            <span className="muted">{pct(percentages[item.key])}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TrendBars({ trend }) {
  const rows = Array.isArray(trend) ? trend : [];
  if (!rows.length) return <p className="muted small">Tur bazlı dağılım için yeterli olay yok.</p>;
  const max = Math.max(...rows.map((row) => Math.max(1, row.positive + row.negative + row.neutral + row.undecided)));
  return (
    <div className="trend-bars">
      {rows.map((row) => {
        const total = Math.max(1, row.positive + row.negative + row.neutral + row.undecided);
        return (
          <div className="trend-col" key={row.round} title={`Tur ${row.round}: ${row.positive} olumlu, ${row.negative} olumsuz, ${row.neutral} nötr, ${row.undecided} kararsız`}>
            <div className="trend-stack" style={{ height: `${Math.max(8, (total / max) * 100)}%` }}>
              {STANCE_META.map((item) => {
                const value = row[item.key] || 0;
                if (!value) return null;
                return <span key={item.key} style={{ height: `${(value / total) * 100}%`, background: item.color }} />;
              })}
            </div>
            <span className="trend-label">{row.round}</span>
          </div>
        );
      })}
    </div>
  );
}

function KeywordChips({ rows }) {
  if (!rows?.length) return <span className="muted small">Belirgin tema yok</span>;
  return (
    <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
      {rows.map((row) => (
        <span className="attr-chip" key={`${row.label}-${row.count}`}>{row.label} · {row.count}</span>
      ))}
    </div>
  );
}

export default function ReportDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    api(`/api/runs/${id}/insights`).then(setData).catch((e) => setErr(e.message));
  }, [id]);

  async function download(format) {
    setBusy(format);
    setErr(null);
    try {
      await downloadReport(id, format);
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  if (err && !data) return (<><p className="error">{err}</p><Link className="btn" to="/app/reports">Raporlara dön</Link></>);
  if (!data) return <div className="shell-loading" style={{ minHeight: 220 }}><div className="spinner" /></div>;

  const run = data.run ?? {};
  const summary = data.summary ?? {};
  const maxAction = Math.max(1, ...(data.actions ?? []).map((row) => row.count));

  return (
    <>
      <div className="detail-head">
        <div>
          <span className="crumb"><Link to="/app/reports">Raporlar</Link><Icon name="chevron" size={13} /> {run.project_name}</span>
          <h2>Simülasyon analizi</h2>
          <div className="row" style={{ marginTop: 8 }}>
            <span className="badge ok">rapor hazır</span>
            <span className="badge no-dot">{run.template_key}</span>
            <span className="badge no-dot">{(run.language ?? "tr").toUpperCase()}</span>
            <Link className="badge no-dot" to={`/app/runs/${run.id}`}>{String(run.id).slice(0, 8)}</Link>
          </div>
        </div>
        <div className="row">
          <button className="btn" type="button" disabled={busy === "md"} onClick={() => download("md")}>Markdown</button>
          <button className="btn btn-primary" type="button" disabled={busy === "pdf"} onClick={() => download("pdf")}><Icon name="doc" size={15} /> PDF raporu</button>
        </div>
      </div>

      {err && <p className="error">{err}</p>}

      <div className="notice"><Icon name="bell" size={15} /><span>Bu analiz yapay zekâ ajanlarının simülasyon çıktısıdır; gerçek anket veya saha araştırması yerine geçmez.</span></div>

      <div className="stat-grid">
        <div className="card stat"><div className="stat-label">Katılımcı</div><div className="stat-value">{summary.total ?? 0}</div><div className="stat-sub">{data.audience_size ?? summary.total ?? 0} ajanlık kitleden</div></div>
        <div className="card stat"><div className="stat-label">Olumlu görüş</div><div className="stat-value" style={{ color: "#4ade80" }}>{pct(summary.percentages?.positive)}</div><div className="stat-sub">{summary.positive ?? 0} katılımcı</div></div>
        <div className="card stat"><div className="stat-label">Olumsuz görüş</div><div className="stat-value" style={{ color: "#fb7185" }}>{pct(summary.percentages?.negative)}</div><div className="stat-sub">{summary.negative ?? 0} katılımcı</div></div>
        <div className="card stat"><div className="stat-label">Kararsız</div><div className="stat-value" style={{ color: "#fbbf24" }}>{pct(summary.percentages?.undecided)}</div><div className="stat-sub">{summary.undecided ?? 0} katılımcı</div></div>
      </div>

      <div className="grid-2">
        <div className="card card-pad">
          <div className="row-between" style={{ marginBottom: 12 }}>
            <h3>Görüş dağılımı</h3>
            <span className="badge no-dot">{summary.total ?? 0} kişi</span>
          </div>
          <Donut summary={summary} />
          <SentimentBar summary={summary} />
          {summary.approval_rate != null && (
            <p className="small muted" style={{ marginTop: 10 }}>Olumlu / olumsuz oranı: <strong>{pct(summary.approval_rate)}</strong> olumlu</p>
          )}
        </div>

        <div className="card card-pad">
          <div className="row-between" style={{ marginBottom: 12 }}>
            <div><h3>Tur bazlı eğilim</h3><p className="small muted">Her turda açıklanan görüşlerin dağılımı</p></div>
            <span className="badge no-dot">{data.rounds ?? 0} tur · {data.events ?? 0} olay</span>
          </div>
          <TrendBars trend={data.trend} />
          <div className="row" style={{ gap: 12, flexWrap: "wrap", marginTop: 10 }}>
            {STANCE_META.map((item) => <span className="small" key={item.key}><span className="legend-dot" style={{ background: item.color, display: "inline-block", marginRight: 5 }} />{item.label}</span>)}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card card-pad">
          <h3 style={{ marginBottom: 12 }}>Aksiyonlar</h3>
          <div className="metric-list">
            {(data.actions ?? []).map((row) => (
              <div className="metric-row" key={row.action}>
                <div className="metric-top"><span>{row.action}</span><strong>{row.count} <span className="muted small">({pct(row.percentage)})</span></strong></div>
                <div className="metric-track"><span style={{ width: `${(row.count / maxAction) * 100}%` }} /></div>
              </div>
            ))}
            {(data.actions ?? []).length === 0 && <p className="muted small">Aksiyon kaydı yok.</p>}
          </div>
        </div>

        <div className="card card-pad">
          <h3 style={{ marginBottom: 12 }}>Platform dağılımı</h3>
          <div className="table-wrap">
            <table className="tbl compact">
              <thead><tr><th>Platform</th><th className="num">Olumlu</th><th className="num">Olumsuz</th><th className="num">Nötr</th><th className="num">Kararsız</th></tr></thead>
              <tbody>
                {(data.platforms ?? []).map((row) => (
                  <tr key={row.platform}>
                    <td>{row.platform}</td>
                    <td className="num">{row.positive}</td>
                    <td className="num">{row.negative}</td>
                    <td className="num">{row.neutral}</td>
                    <td className="num">{row.undecided}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.emotions?.length > 0 && (
            <>
              <h3 style={{ marginTop: 18, marginBottom: 8 }}>Öne çıkan duygular</h3>
              <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
                {data.emotions.map((row) => <span className="badge no-dot" key={row.label}>{row.label} · {row.count}</span>)}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="card card-pad">
        <div className="row-between" style={{ marginBottom: 12 }}>
          <div><h3>Nedenler ve tekrar eden temalar</h3><p className="small muted">Katılımcıların gönderi hakkında en sık kullandığı kelimeler</p></div>
        </div>
        <div className="grid-4">
          {STANCE_META.map((item) => (
            <div className="reason-card" key={item.key}>
              <div className="reason-head"><span className="legend-dot" style={{ background: item.color }} /><strong>{item.label}</strong><span className="muted small">{summary[item.key] ?? 0} kişi</span></div>
              <KeywordChips rows={data.keywords?.[item.key]} />
            </div>
          ))}
        </div>
      </div>

      <div className="card card-pad">
        <h3 style={{ marginBottom: 12 }}>Temsili katılımcı yorumları</h3>
        <div className="grid-2">
          {STANCE_META.map((item) => (
            (data.quotes?.[item.key] ?? []).slice(0, 2).map((quote, idx) => (
              <div className={`quote-card ${item.tone}`} key={`${item.key}-${idx}`}>
                <div className="quote-head"><span className="badge no-dot">{item.label}</span><span className="small muted">{quote.agent} · Tur {quote.round}</span></div>
                <p>{quote.content}</p>
                <div className="small muted">{quote.action}{quote.emotion ? ` · ${quote.emotion}` : ""}</div>
              </div>
            ))
          ))}
        </div>
        {STANCE_META.every((item) => !(data.quotes?.[item.key] ?? []).length) && (
          <p className="muted small">Bu koşuda yorum metni bulunmuyor.</p>
        )}
      </div>
    </>
  );
}
