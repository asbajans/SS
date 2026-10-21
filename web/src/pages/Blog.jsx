import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmtDate } from "../api.js";
import Icon from "../icons.jsx";

export default function Blog() {
  const [lang, setLang] = useState(() => localStorage.getItem("ss_lang") || "tr");
  const [posts, setPosts] = useState([]);
  const [err, setErr] = useState(null);
  const en = lang === "en";

  useEffect(() => {
    localStorage.setItem("ss_lang", lang);
    api("/api/blog/posts").then(setPosts).catch((e) => setErr(e.message));
  }, [lang]);

  return (
    <div className="landing blog-shell">
      <nav className="landing-nav">
        <Link className="brand" to="/" style={{ textDecoration: "none" }}>
          <span className="brand-mark">SS</span>
          <span className="brand-name">Social Simulation<small>{en ? "community simulation" : "topluluk simülasyonu"}</small></span>
        </Link>
        <div className="row">
          <button className="btn btn-dark btn-sm" type="button" onClick={() => setLang(en ? "tr" : "en")}>{en ? "TR" : "EN"}</button>
          <Link className="btn btn-dark btn-sm" to="/">{en ? "Home" : "Ana sayfa"}</Link>
          <Link className="btn btn-primary btn-sm" to="/register">{en ? "Start free" : "Ücretsiz Başla"}</Link>
        </div>
      </nav>

      <section className="landing-section blog-section">
        <span className="hero-tag"><Icon name="doc" size={15} /> {en ? "Insights" : "İçgörüler"}</span>
        <h1 className="blog-title">{en ? "Research notes & product updates" : "Araştırma notları ve ürün güncellemeleri"}</h1>
        <p className="sub">{en ? "Synthetic communities, simulation methodology and automation." : "Sentetik topluluklar, simülasyon metodolojisi ve otomasyon."}</p>

        {err && <p className="error">{err}</p>}

        <div className="blog-grid">
          {posts.map((p, i) => (
            <Link className="card blog-card" key={p.slug} to={`/blog/${p.slug}`}>
              <span className="blog-index">{String(i + 1).padStart(2, "0")}</span>
              <h3>{en ? p.title_en : p.title_tr}</h3>
              <p>{en ? p.excerpt_en : p.excerpt_tr}</p>
              <div className="blog-meta">
                <span>{fmtDate(p.published_at)}</span>
                <span className="blog-more">{en ? "Read more" : "Devamını oku"} <Icon name="chevron" size={14} /></span>
              </div>
            </Link>
          ))}
        </div>
        {posts.length === 0 && !err && <div className="empty"><span className="empty-icon"><Icon name="doc" size={22} /></span><h3>{en ? "No posts yet" : "Henüz yazı yok"}</h3></div>}
      </section>

      <footer className="landing-foot">
        <div className="legal">
          <Link to="/">{en ? "Home" : "Ana sayfa"}</Link>
          <Link to="/blog">{en ? "Blog" : "Blog"}</Link>
          <Link to="/login">{en ? "Sign in" : "Giriş"}</Link>
        </div>
        <p>Social Simulation © {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}
