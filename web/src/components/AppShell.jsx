import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { api, logout } from "../api.js";
import { useLang } from "../i18n.js";
import Icon from "../icons.jsx";

const NAV = [
  { to: "/app", end: true, icon: "grid", label: "Panoya Başla" },
  { to: "/app/projects", icon: "folder", label: "Projeler" },
  { to: "/app/runs", icon: "activity", label: "Simülasyonlar" },
  { to: "/app/reports", icon: "doc", label: "Raporlar" },
  { to: "/app/api", icon: "box", label: "API & Entegrasyon" },
  { to: "/blog", icon: "doc", label: "Blog" },
];

const NAV_BOTTOM = [
  { to: "/app/billing", icon: "card", label: "Plan & Faturalama" },
  { to: "/app/settings", icon: "sliders", label: "Ayarlar" },
];

const TITLES = [
  ["/app/api", "API & Entegrasyon"],
  ["/app/projects/new", "Yeni Simülasyon"],
  ["/app/projects", "Projeler"],
  ["/app/runs", "Simülasyonlar"],
  ["/app/reports", "Raporlar"],
  ["/app/billing", "Plan & Faturalama"],
  ["/app/settings", "Ayarlar"],
  ["/app/admin/blog", "Blog editörü"],
  ["/app/admin/billing", "Faturalama yönetimi"],
  ["/app/admin", "Yönetim"],
  ["/app", "Genel Bakış"],
];

function pageTitle(path) {
  if (/^\/app\/projects\/.+/.test(path)) return "Proje Detayı";
  if (/^\/app\/runs\/.+/.test(path)) return "Simülasyon Detayı";
  if (/^\/app\/reports\/.+/.test(path)) return "Rapor Analizi";
  const hit = TITLES.find(([p]) => path.startsWith(p));
  return hit ? hit[1] : "Social Simulation";
}

export default function AppShell() {
  const [user, setUser] = useState(null);
  const [err, setErr] = useState(null);
  const [open, setOpen] = useState(false);
  const [lang, toggleLang] = useLang();
  const loc = useLocation();

  useEffect(() => {
    api("/api/auth/me").then(setUser).catch((e) => setErr(e.message));
  }, []);

  useEffect(() => { setOpen(false); }, [loc.pathname]);

  if (err) {
    return (
      <div className="shell-loading">
        <p className="error">{err}</p>
        <Link className="btn btn-primary" to="/login">Girişe dön</Link>
      </div>
    );
  }
  if (!user) return <div className="shell-loading"><div className="spinner" /></div>;

  const initials = (user.email || "?").slice(0, 2).toUpperCase();

  return (
    <div className={`shell${open ? " nav-open" : ""}`}>
      <aside className="sidebar">
        <Link className="brand" to="/app" aria-label="Social Simulator">
          <img src="/logo-light.png" alt="Social Simulator" />
        </Link>
        <div className="nav-group-label">Çalışma Alanı</div>
        <nav className="nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className="nav-item">
              <Icon name={n.icon} />
              <span>{n.label}</span>
            </NavLink>
          ))}
          {user.is_admin && (
            <>
              <NavLink to="/app/admin" className="nav-item" end>
                <Icon name="shield" />
                <span>Yönetim</span>
              </NavLink>
              <NavLink to="/app/admin/blog" className="nav-item">
                <Icon name="doc" />
                <span>Blog editörü</span>
              </NavLink>
            </>
          )}
        </nav>
        <div className="nav-group-label">Hesap</div>
        <nav className="nav">
          {NAV_BOTTOM.map((n) => (
            <NavLink key={n.to} to={n.to} className="nav-item">
              <Icon name={n.icon} />
              <span>{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="user-chip">
            <span className="avatar">{initials}</span>
            <span className="user-meta">
              <span className="user-mail">{user.email}</span>
              <span className="plan-pill">{user.plan ?? "free"}</span>
            </span>
          </div>
          <button className="nav-item as-button" type="button" onClick={logout}>
            <Icon name="logout" />
            <span>Çıkış</span>
          </button>
        </div>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <button className="burger" type="button" aria-label="Menü" onClick={() => setOpen((v) => !v)}>
            <span /><span /><span />
          </button>
          <h1 className="page-title">{pageTitle(loc.pathname)}</h1>
          <div className="topbar-right">
            <button className="lang-pill" type="button" onClick={toggleLang} title="Dil / Language" aria-label="Language">
              <span className={lang === "tr" ? "on" : ""}>TR</span>
              <span className={lang === "en" ? "on" : ""}>EN</span>
            </button>
            <span className="sim-badge" title="Tüm çıktılar simülasyon ürünüdür">
              <Icon name="bell" size={14} /> Simülasyon
            </span>
            <Link className="btn btn-primary btn-sm" to="/app/projects/new">
              <Icon name="plus" size={15} /> Yeni Simülasyon
            </Link>
          </div>
        </header>
        <main className="content"><Outlet context={user} /></main>
        <footer className="app-foot">
          Tüm çıktılar simülasyon ürünüdür; gerçek anket veya kamuoyu ölçümü değildir.
        </footer>
      </div>
    </div>
  );
}
