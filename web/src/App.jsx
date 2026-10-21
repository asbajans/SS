import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, fmtTokens, TEMPLATES } from "./api.js";
import Icon from "./icons.jsx";

const TEMPLATE_EN = {
  market_research: ["Market Research", "Synthetic consumer community on segments, competitors and price perception."],
  public_opinion: ["Public Opinion & Crisis", "Simulate discourse, trust and diffusion dynamics around an issue."],
  concept_test: ["Product Concept", "Virtual user feedback for feature prioritization and jobs-to-be-done."],
  price_probe: ["Price Testing", "Measure willingness-to-pay curves and price-hook reactions."],
  policy_review: ["Policy & Regulation", "Stakeholder reactions, support–opposition balance and conflict maps."],
  fiction_review: ["Fictional Worlds", "Character consistency, relationship dynamics and community response."],
};

const FALLBACK_PLANS = [
  { key: "free", price: 0, token_budget: 1_000_000, agents: 50, rounds: 20 },
  { key: "starter", price: 29, token_budget: 8_000_000, agents: 150, rounds: 40 },
  { key: "pro", price: 99, token_budget: 25_000_000, agents: 300, rounds: 90 },
];

const COPY = {
  tr: {
    navSub: "topluluk simülasyonu",
    login: "Giriş",
    start: "Ücretsiz Başla",
    heroTag: "Sentetik topluluk simülasyonu",
    heroTitleA: "Geleceği tahmin etmek için",
    heroTitleEm: "binlerce ajanı",
    heroTitleB: "aynı dünyaya yerleştirin",
    heroLead: "Konunuzu tanımlayın; sentetik bir topluluk kamuoyu, pazar veya kriz senaryonuzda etkileşime girsin. Çıktı: kaynakçalı, denetlenebilir ve",
    heroLeadStrong: "simülasyon etiketli",
    heroLeadEnd: "raporlar.",
    heroCta: "Simülasyon oluştur",
    heroCta2: "Zaten üyeyim",
    stats: [["6", "hazır şablon"], ["300", "ajana kadar"], ["120", "tura kadar derinlik"], ["$0,10+", "simülasyon başına"]],
    disclaimer: "Tüm çıktılar simülasyon ürünüdür; gerçek anket veya kamuoyu ölçümü değildir.",
    templatesTitle: "Altı hazır araştırma şablonu",
    templatesSub: "Konu-agnostik motor; her şablon kendi ontoloji ve aksiyon uzayıyla gelir.",
    stepsTitle: "Üç adımda topluluk araştırması",
    stepsSub: "Kurulum yok, dış servis yok — her şey yerel altyapıda çalışır.",
    steps: [
      ["Kaynakları yükle", "Rapor, brief veya metin dosyalarını projeye ekleyin; sistem bilgi tabanını kurar."],
      ["Topluluğu simüle et", "Yüzlerce sentetik ajan, kişilikleri ve hatıralarıyla forum benzeri ortamda etkileşime girer."],
      ["Raporu alın", "Olaylara ve belgelere dayalı, simülasyon etiketli detaylı analiz raporu üretin."],
    ],
    popular: "Popüler",
    pricingTitle: "Şeffaf fiyatlandırma",
    pricingSub: "Aylık token bütçesiyle başlayın; ihtiyaç oldukça kredi ekleyin. Gizli ücret yok.",
    perMonth: "/ay",
    free: "Ücretsiz",
    starter: "Başlangıç",
    pro: "Pro",
    current: "Mevcut plan",
    choose: "Planı seç",
    tokens: "token / ay",
    agents: "ajana kadar",
    rounds: "tur derinlik",
    creditsNote: "Ek kredi paketi: 5M token — $19 (tek seferlik).",
    ctaTitle: "İlk simülasyonunuzu bugün çalıştırın",
    ctaText: "Ücretsiz plan aylık 1M token ile 50 ajanlık simülasyonlara izin verir.",
    ctaButton: "Hesap oluştur",
    tos: "Kullanım Şartları",
    privacy: "Gizlilik Bildirimi",
    dmca: "DMCA",
    contact: "İletişim",
    footNote: "Social Simulation — sentetik topluluk simülasyonu platformu. Ajanlar tamamen kurgusaldır; gerçek kişisel veri toplanmaz.",
  },
  en: {
    navSub: "community simulation",
    login: "Sign in",
    start: "Start free",
    heroTag: "Synthetic community simulation",
    heroTitleA: "Place",
    heroTitleEm: "thousands of agents",
    heroTitleB: "in the same world to see what comes next",
    heroLead: "Describe your topic; a synthetic community engages with your public opinion, market or crisis scenario. Output: sourced, auditable and",
    heroLeadStrong: "simulation-labeled",
    heroLeadEnd: "reports.",
    heroCta: "Create simulation",
    heroCta2: "I already have an account",
    stats: [["6", "ready templates"], ["300", "agents max"], ["120", "rounds deep"], ["$0.10+", "per simulation"]],
    disclaimer: "All outputs are simulation artifacts; they are not real polls or public opinion measurements.",
    templatesTitle: "Six ready research templates",
    templatesSub: "Topic-agnostic engine; every template ships with its own ontology and action space.",
    stepsTitle: "Community research in three steps",
    stepsSub: "No setup, no third-party services — everything runs on local infrastructure.",
    steps: [
      ["Upload sources", "Add reports, briefs or text files to a project; the system builds a knowledge base."],
      ["Simulate the community", "Hundreds of synthetic agents interact in a forum-like space with personalities and memories."],
      ["Get the report", "Produce a detailed, simulation-labeled analysis grounded in events and documents."],
    ],
    popular: "Popular",
    pricingTitle: "Transparent pricing",
    pricingSub: "Start with a monthly token budget; add credits as you grow. No hidden fees.",
    perMonth: "/mo",
    free: "Free",
    starter: "Starter",
    pro: "Pro",
    current: "Current plan",
    choose: "Choose plan",
    tokens: "tokens / mo",
    agents: "agents max",
    rounds: "round depth",
    creditsNote: "Extra credit pack: 5M tokens — $19 (one-time).",
    ctaTitle: "Run your first simulation today",
    ctaText: "The free plan includes 1M tokens per month and simulations with up to 50 agents.",
    ctaButton: "Create account",
    tos: "Terms of Service",
    privacy: "Privacy Notice",
    dmca: "DMCA",
    contact: "Contact",
    footNote: "Social Simulation — synthetic community simulation platform. Agents are entirely fictional; no real personal data is collected.",
  },
};

function CountUp({ value }) {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    let raf;
    const start = performance.now();
    const duration = 1100;
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      setCurrent(Math.round(value * (1 - (1 - progress) ** 3)));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{current}</>;
}

export default function App() {
  const [lang, setLang] = useState(() => localStorage.getItem("ss_lang") || "tr");
  const [plans, setPlans] = useState(FALLBACK_PLANS);
  const t = COPY[lang] ?? COPY.tr;

  useEffect(() => {
    localStorage.setItem("ss_lang", lang);
  }, [lang]);

  useEffect(() => {
    const nodes = document.querySelectorAll(".landing .reveal");
    if (!("IntersectionObserver" in window)) {
      nodes.forEach((node) => node.classList.add("visible"));
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [lang]);

  useEffect(() => {
    api("/api/billing/plans")
      .then((data) => {
        if (Array.isArray(data?.plans) && data.plans.length > 0) setPlans(data.plans);
      })
      .catch(() => {});
  }, []);

  function planName(key) {
    return t[key] ?? key;
  }

  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="brand">
          <span className="brand-mark">SS</span>
          <span className="brand-name">
            Social Simulation
            <small>{t.navSub}</small>
          </span>
        </div>
        <div className="row">
          <button className="btn btn-dark btn-sm" type="button" onClick={() => setLang(lang === "tr" ? "en" : "tr")}>
            {lang === "tr" ? "EN" : "TR"}
          </button>
          <Link className="btn btn-dark btn-sm" to="/blog">Blog</Link>
          <Link className="btn btn-dark btn-sm" to="/login">{t.login}</Link>
          <Link className="btn btn-primary btn-sm" to="/register">{t.start}</Link>
        </div>
      </nav>

      <header className="landing-hero">
        <div className="hero-orbs" aria-hidden="true"><span /><span /><span /></div>
        <div className="hero-float hero-float-a" aria-hidden="true">+1.284 <small>{lang === "tr" ? "ajan" : "agents"}</small></div>
        <div className="hero-float hero-float-b" aria-hidden="true">sentiment ↑ <small>+%12</small></div>
        <span className="hero-tag"><Icon name="users" size={15} /> {t.heroTag}</span>
        <h1>
          {t.heroTitleA} <em>{t.heroTitleEm}</em> {t.heroTitleB}
        </h1>
        <p className="lead">
          {t.heroLead}{" "}
          <strong style={{ color: "#e8edf7" }}>{t.heroLeadStrong}</strong> {t.heroLeadEnd}
        </p>
        <div className="hero-cta">
          <Link className="btn btn-primary" to="/register"><Icon name="play" size={16} /> {t.heroCta}</Link>
          <Link className="btn btn-dark" to="/login">{t.heroCta2}</Link>
        </div>
        <div className="hero-stats">
          {t.stats.map(([n, label]) => (
            <div key={label}><b>{/^\d+$/.test(n) ? <CountUp value={Number(n)} /> : n}</b><span>{label}</span></div>
          ))}
        </div>
        <div className="disclaimer-strip">{t.disclaimer}</div>
      </header>

      <div className="landing-marquee" aria-hidden="true">
        <div className="marquee-track">
          {[...TEMPLATES, ...TEMPLATES].map((tpl, i) => (
            <span key={`${tpl.key}-${i}`}>{lang === "en" ? (TEMPLATE_EN[tpl.key]?.[0] ?? tpl.name) : tpl.name}<i>✳</i></span>
          ))}
        </div>
      </div>

      <section className="landing-section reveal">
        <h2>{t.templatesTitle}</h2>
        <p className="sub">{t.templatesSub}</p>
        <div className="feature-grid">
          {TEMPLATES.map((tpl, i) => {
            const [name, desc] = lang === "en" ? TEMPLATE_EN[tpl.key] ?? [tpl.name, tpl.desc] : [tpl.name, tpl.desc];
            return (
              <article className="feature" key={tpl.key}>
                <span className="f-icon" style={{ background: i % 2 === 0 ? "var(--grad)" : "linear-gradient(135deg,#0d9488,#14b8a6)" }}>
                  <Icon name="box" />
                </span>
                <h3>{name}</h3>
                <p>{desc}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="landing-section reveal" style={{ paddingTop: 8 }}>
        <h2>{t.stepsTitle}</h2>
        <p className="sub">{t.stepsSub}</p>
        <div className="steps-row">
          {t.steps.map(([title, desc], i) => (
            <div className="step-card" key={title}>
              <span className="n">{i + 1}</span>
              <h3>{title}</h3>
              <p>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-pricing reveal">
        <h2>{t.pricingTitle}</h2>
        <p className="sub">{t.pricingSub}</p>
        <div className="grid-3">
          {plans.map((p) => {
            const isFree = p.key === "free";
            return (
              <div className={`card plan-card${p.key === "pro" ? " current" : ""}`} key={p.key}>
                {p.key === "pro" && <span className="plan-tag">{t.popular.toUpperCase()}</span>}
                <h3>{planName(p.key)}</h3>
                <div className="plan-price">${p.price}<span> {p.price > 0 ? t.perMonth : ""}</span></div>
                <ul className="plan-feats">
                  <li><Icon name="check" size={15} /> {fmtTokens(p.token_budget)} {t.tokens}</li>
                  <li><Icon name="check" size={15} /> {p.agents} {t.agents}</li>
                  <li><Icon name="check" size={15} /> {p.rounds} {t.rounds}</li>
                </ul>
                <Link className={`btn${isFree ? "" : " btn-primary"} btn-block`} to="/register">
                  {isFree ? t.start : t.choose}
                </Link>
              </div>
            );
          })}
        </div>
        <p className="pricing-note">{t.creditsNote}</p>
      </section>

      <section className="landing-cta-band">
        <h2>{t.ctaTitle}</h2>
        <p>{t.ctaText}</p>
        <Link className="btn btn-primary btn-lg" to="/register">
          <Icon name="arrowLeft" size={16} style={{ transform: "rotate(180deg)" }} /> {t.ctaButton}
        </Link>
      </section>

      <footer className="landing-foot">
        <div className="legal">
          <Link to="/blog">Blog</Link>
          <a href="#tos">{t.tos}</a>
          <a href="#privacy">{t.privacy}</a>
          <a href="#dmca">{t.dmca}</a>
          <a href="#contact">{t.contact}</a>
        </div>
        <p>
          {t.footNote} © {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
}
