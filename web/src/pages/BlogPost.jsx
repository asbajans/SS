import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, fmtDate } from "../api.js";
import AdSlot from "../components/AdSlot.jsx";
import SeoHead from "../components/SeoHead.jsx";
import Icon from "../icons.jsx";

function Body({ text }) {
  return text.split(/\n\n+/).map((block, i) => {
    const lines = block.split("\n");
    if (block.startsWith("## ")) {
      return <h2 key={i} className="blog-h2">{block.slice(3)}</h2>;
    }
    if (lines.every((line) => line.startsWith("- "))) {
      return <ul key={i} className="blog-list">{lines.map((line) => <li key={line}>{line.slice(2)}</li>)}</ul>;
    }
    return <p key={i}>{block}</p>;
  });
}

export default function BlogPostPage() {
  const { slug } = useParams();
  const [lang, setLang] = useState(() => localStorage.getItem("ss_lang") || "tr");
  const [post, setPost] = useState(null);
  const [err, setErr] = useState(null);
  const en = lang === "en";

  useEffect(() => {
    localStorage.setItem("ss_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    setPost(null);
    setErr(null);
    api(`/api/blog/posts/${encodeURIComponent(slug)}`)
      .then((data) => setPost(data))
      .catch((e) => setErr(e.message));
  }, [slug]);

  const jsonLd = post
    ? {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        headline: en ? post.title_en : post.title_tr,
        description: post.meta_description_en || post.excerpt_en || post.meta_description_tr || post.excerpt_tr,
        url: `${window.location.origin}/blog/${post.slug}`,
        datePublished: post.published_at,
        dateModified: post.updated_at,
        inLanguage: en ? "en" : "tr",
        author: { "@type": "Organization", name: "Social Simulator" },
        publisher: { "@type": "Organization", name: "Social Simulator" },
        ...(post.og_image ? { image: post.og_image } : {}),
        ...(post.focus_keyword_tr ? { keywords: post.focus_keyword_tr } : {}),
      }
    : null;

  return (
    <div className="landing blog-shell">
      <SeoHead
        title={post ? (en ? post.title_en : post.title_tr) : ""}
        description={post
          ? (en ? post.meta_description_en || post.excerpt_en : post.meta_description_tr || post.excerpt_tr)
          : ""}
        ogImage={post?.og_image}
        canonical={post ? `/blog/${post.slug}` : ""}
        noindex={Boolean(post?.noindex)}
        ogType="article"
        jsonLd={jsonLd}
      />
      <nav className="landing-nav">
        <Link className="brand" to="/" aria-label="Social Simulator">
          <img src="/logo-light.png" alt="Social Simulator" />
        </Link>
        <div className="row">
          <button className="btn btn-dark btn-sm" type="button" onClick={() => setLang(en ? "tr" : "en")}>{en ? "TR" : "EN"}</button>
          <Link className="btn btn-dark btn-sm" to="/blog"><Icon name="arrowLeft" size={14} /> {en ? "All posts" : "Tüm yazılar"}</Link>
          <Link className="btn btn-primary btn-sm" to="/register">{en ? "Start free" : "Ücretsiz Başla"}</Link>
        </div>
      </nav>

      <article className="blog-article">
        {err && <p className="error">{err}</p>}
        {!post && !err && <div className="spinner" />}
        {post && (
          <>
            <span className="blog-date">{fmtDate(post.published_at)}</span>
            <h1>{en ? post.title_en : post.title_tr}</h1>
            <p className="blog-lead">{en ? post.excerpt_en : post.excerpt_tr}</p>
            <div className="blog-body"><Body text={en ? post.body_en : post.body_tr} /></div>
            <div className="notice" style={{ marginTop: 26 }}>
              <Icon name="bell" size={15} />
              <span>{en ? "All outputs are simulation artifacts, not real polls." : "Tüm çıktılar simülasyon ürünüdür; gerçek anket değildir."}</span>
            </div>
            <div className="row" style={{ marginTop: 18 }}>
              <Link className="btn btn-primary" to="/register">{en ? "Try it free" : "Ücretsiz deneyin"}</Link>
              <Link className="btn" to="/blog">{en ? "Back to blog" : "Bloga dön"}</Link>
            </div>
            <AdSlot slot="secondary" className="ad-slot-inline" />
          </>
        )}
      </article>

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
