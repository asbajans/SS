import { useEffect, useRef, useState } from "react";
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
  const [topbarH, setTopbarH] = useState(56);
  const [lang, toggleLang] = useLang();
  const loc = useLocation();
  const topbarRef = useRef(null);

  useEffect(() => {
    api("/api/auth/me").then(setUser).catch((e) => setErr(e.message));
  }, []);

  useEffect(() => { setOpen(false); }, [loc.pathname]);

  useEffect(() => {
    const el = topbarRef.current;
    if (!el) return;
    const apply = () => setTopbarH(el.getBoundingClientRect().height);
    apply();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(apply) : null;
    if (ro) { ro.observe(el); return () => ro.disconnect(); }
    window.addEventListener("resize", apply);
    return () => window.removeEventListener("resize", apply);
  }, [user]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onResize = () => {
      if (window.innerWidth > 860) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const root = document.documentElement;
    root.classList.add("nav-locked");
    return () => root.classList.remove("nav-locked");
  }, [open]);

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
    <div className={`shell${open ? " nav-open" : ""}`} style={{ "--topbar-h": `${topbarH}px` }}>
      <button
        className="nav-backdrop"
        type="button"
        aria-label="Menüyü kapat"
        tabIndex={open ? 0 : -1}
        onClick={() => setOpen(false)}
      />
      <aside className="sidebar" id="panel-sidebar">
        <div className="sidebar-head">
          <Link className="brand" to="/app" aria-label="Social Simulator">
            <img src="/logo-light.png" alt="Social Simulator" />
          </Link>
          <button className="nav-close" type="button" aria-label="Menüyü kapat" onClick={() => setOpen(false)}>
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className="nav-group-label">Çalışma Alanı</div>
        <nav className="nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className="nav-item" onClick={() => setOpen(false)}>
              <Icon name={n.icon} />
              <span>{n.label}</span>
            </NavLink>
          ))}
          {user.is_admin && (
            <>
              <NavLink to="/app/admin" className="nav-item" end onClick={() => setOpen(false)}>
                <Icon name="shield" />
                <span>Yönetim</span>
              </NavLink>
              <NavLink to="/app/admin/blog" className="nav-item" onClick={() => setOpen(false)}>
                <Icon name="doc" />
                <span>Blog editörü</span>
              </NavLink>
            </>
          )}
        </nav>
        <div className="nav-group-label">Hesap</div>
        <nav className="nav">
          {NAV_BOTTOM.map((n) => (
            <NavLink key={n.to} to={n.to} className="nav-item" onClick={() => setOpen(false)}>
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
        <header className="topbar" ref={topbarRef}>
          <button
            className={`burger${open ? " is-open" : ""}`}
            type="button"
            aria-label="Menü"
            aria-expanded={open}
            aria-controls="panel-sidebar"
            onClick={() => setOpen((v) => !v)}
          >
            <span /><span /><span />
          </button>
          <h1 className="page-title">{pageTitle(loc.pathname)}</h1>
          <div className="topbar-right">
            <button className="lang-pill" type="button" onClick={toggleLang} title="Dil / Language" aria-label="Language">
              <span className={lang === "tr" ? "on" : ""}>TR</span>
              <span className={lang === "en" ? "on" : ""}>EN</span>
            </button>
            <Link className="btn btn-primary btn-sm topbar-new" to="/app/projects/new">
              <Icon name="plus" size={15} /> <span className="topbar-new-label">Yeni Simülasyon</span>
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
