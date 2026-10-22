import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, fmtTokens, getToken } from "./api.js";
import AdSlot from "./components/AdSlot.jsx";
import SeoHead from "./components/SeoHead.jsx";

const FALLBACK_PLANS = [
  { key: "free", price: 0, token_budget: 1_000_000, agents: 50, rounds: 20 },
  { key: "starter", price: 29, token_budget: 8_000_000, agents: 150, rounds: 40 },
  { key: "pro", price: 99, token_budget: 25_000_000, agents: 300, rounds: 90 },
];

const COPY = {
  tr: {
    navFeatures: "Özellikler",
    navHow: "Nasıl çalışır",
    navPricing: "Fiyatlandırma",
    navBlog: "Blog",
    panel: "Kontrol Paneli",
    login: "Giriş",
    heroTag: "Sentetik topluluk simülasyonu",
    heroA: "Ne istediğinizi söyleyin.",
    heroB: "Ben simüle edeyim.",
    heroSub:
      "Binlerce yapay zeka personası oluşturun; kampanyanızı yayına almadan test edin, etkileşim sinyallerini ve duygu değişimini izleyin.",
    prompts: [
      "Yeni kampanyamız 25-40 yaş kitlede nasıl karşılanır?",
      "Fiyat artışımıza sosyal medyada gelecek tepkileri simüle et",
      "Markamız için bir kriz senaryosu çalıştır",
      "Yeni ürün konseptimize gelen itirazları gör",
    ],
    promptBtn: "Simüle et",
    cta: "Simülasyon Başlat",
    cta2: "Kontrol Paneli",
    stats: [
      ["6", "hazır araştırma şablonu"],
      ["300", "ajana kadar ölçek"],
      ["120", "tura kadar derinlik"],
    ],
    disclaimer:
      "Tüm çıktılar simülasyon ürünüdür; gerçek anket veya kamuoyu ölçümü değildir.",
    featuresTitle: "Hayal ettiğiniz her şey. Simüle edildi.",
    featuresSub: "Konuya özel sentetik topluluklar, ölçülebilir davranış sinyalleri ve denetlenebilir raporlar.",
    features: [
      ["◉", "Persona sürüsü", "Gerçekçi inanç, ruh hali ve alışkanlıklara sahip sentetik kitleler."],
      ["↗", "Etkileşim sinyalleri", "Paylaşmadan önce beğeni, itiraz ve yayılma eğilimlerini görün."],
      ["⚠", "Kriz provası", "Markanızı geri tepme ve kriz senaryolarına karşı güvenle test edin."],
      ["⬡", "Ağ görünümü", "Fikirlerin topluluklar arasında düğüm düğüm nasıl yayıldığını izleyin."],
      ["▦", "Çoklu platform", "X, Instagram, TikTok, LinkedIn ve Reddit davranışlarını modelleyin."],
      ["✦", "Anında rapor", "Her koşudan sonra yapay zeka destekli içgörü ve aksiyon planı."],
    ],
    howTitle: "Geleceğe üç adım",
    steps: [
      ["01", "Hedefinizi tanımlayın", "Konuyu, hedef kitleyi ve senaryoyu sade bir dille anlatın."],
      ["02", "Yapay zeka dünyayı kurar", "Ontoloji, personası ve etkileşim ağı otomatik oluşturulur."],
      ["03", "İzleyin ve optimize edin", "Turlar ilerledikçe sinyalleri okuyun, raporu indirin ve karar verin."],
    ],
    pricingTitle: "Gerçekliğinizi seçin",
    pricingSub: "Aylık token bütçesiyle başlayın; ihtiyaç oldukça kredi ekleyin. Gizli ücret yok.",
    popular: "Popüler",
    perMonth: "/ay",
    free: "Ücretsiz",
    starter: "Başlangıç",
    pro: "Pro",
    tokens: "token / ay",
    agents: "ajana kadar",
    rounds: "tur derinlik",
    choose: "Planı seç",
    startFree: "Ücretsiz başla",
    creditsNote: "Ek kredi paketi: 5M token — $19 (tek seferlik).",
    finalTitle: "Ne isterseniz — simüle edebilirim.",
    finalCta: "Simülatöre gir",
    footerNote:
      "Social Simulator — sentetik topluluk simülasyonu platformu. Ajanlar tamamen kurgusaldır; gerçek kişisel veri toplanmaz.",
    tos: "Kullanım Şartları",
    privacy: "Gizlilik",
    dmca: "DMCA",
    contact: "İletişim",
    demo: "Örnek sinyal",
    virality: "YAYILMA",
    sentiment: "DUYGU",
  },
  en: {
    navFeatures: "Features",
    navHow: "How it works",
    navPricing: "Pricing",
    navBlog: "Blog",
    panel: "Control Panel",
    login: "Sign in",
    heroTag: "Synthetic community simulation",
    heroA: "Tell me what you want.",
    heroB: "I'll simulate it.",
    heroSub:
      "Generate thousands of AI personas, test campaigns before launch and watch engagement signals and sentiment shift in real time.",
    prompts: [
      "How will our new campaign land with a 25-40 audience?",
      "Simulate the social reaction to our price increase",
      "Run a crisis rehearsal for our brand",
      "Show me the objections to our new product concept",
    ],
    promptBtn: "Simulate",
    cta: "Launch Simulation",
    cta2: "Control Panel",
    stats: [
      ["6", "ready research templates"],
      ["300", "agents max"],
      ["120", "rounds deep"],
    ],
    disclaimer:
      "All outputs are simulation artifacts; they are not real polls or public opinion measurements.",
    featuresTitle: "Anything you imagine. Simulated.",
    featuresSub: "Topic-specific synthetic communities, measurable behavior signals and auditable reports.",
    features: [
      ["◉", "Persona swarm", "Realistic audiences with unique beliefs, moods and habits."],
      ["↗", "Engagement signals", "See likes, objections and spread before you publish."],
      ["⚠", "Crisis rehearsal", "Stress-test your brand against backlash scenarios safely."],
      ["⬡", "Network view", "See how ideas travel through communities, node by node."],
      ["▦", "Multi-platform", "X, Instagram, TikTok, LinkedIn and Reddit — all emulated."],
      ["✦", "Instant reports", "AI-written insights and action plans after every run."],
    ],
    howTitle: "Three steps to the future",
    steps: [
      ["01", "Describe your goal", "Explain the topic, audience and scenario in plain language."],
      ["02", "AI builds the world", "Ontology, personas and the interaction network are generated."],
      ["03", "Watch and optimize", "Read signals as rounds unfold, download the report and decide."],
    ],
    pricingTitle: "Choose your reality",
    pricingSub: "Start with a monthly token budget; add credits as you grow. No hidden fees.",
    popular: "Popular",
    perMonth: "/mo",
    free: "Free",
    starter: "Starter",
    pro: "Pro",
    tokens: "tokens / mo",
    agents: "agents max",
    rounds: "round depth",
    choose: "Choose plan",
    startFree: "Start free",
    creditsNote: "Extra credit pack: 5M tokens — $19 (one-time).",
    finalTitle: "Whatever you want — I can do it.",
    finalCta: "Enter the simulator",
    footerNote:
      "Social Simulator — synthetic community simulation platform. Agents are entirely fictional; no real personal data is collected.",
    tos: "Terms",
    privacy: "Privacy",
    dmca: "DMCA",
    contact: "Contact",
    demo: "Demo signal",
    virality: "VIRALITY",
    sentiment: "SENTIMENT",
  },
};

const NODES = [
  [260, 214, 13],
  [176, 150, 7],
  [214, 279, 6],
  [126, 232, 5],
  [306, 125, 6],
  [360, 190, 5],
  [330, 275, 7],
  [224, 96, 4],
  [92, 164, 5],
  [404, 252, 4],
  [170, 338, 4],
  [300, 346, 5],
  [364, 324, 4],
  [430, 158, 4],
  [66, 264, 4],
  [236, 178, 4],
  [138, 112, 4],
  [392, 96, 3],
];

const EDGES = [
  [0, 1], [0, 2], [0, 4], [0, 5], [0, 6], [0, 15],
  [1, 3], [1, 7], [1, 8], [1, 15], [1, 16],
  [2, 3], [2, 10], [2, 11], [2, 7],
  [4, 7], [4, 17], [4, 5],
  [5, 9], [5, 13], [5, 6],
  [6, 9], [6, 11], [6, 12],
  [3, 14], [10, 14], [11, 12],
];

function NetworkGraph({ labels }) {
  return (
    <div className="lp-visual">
      <div className="lp-visual-glow" aria-hidden="true" />
      <svg className="lp-network" viewBox="0 0 500 420" role="img" aria-label="Synthetic community network">
        <defs>
          <radialGradient id="lp-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#a5f3fc" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#67e8f9" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx="260" cy="214" rx="210" ry="170" fill="none" stroke="rgba(103,232,249,.08)" strokeDasharray="2 12" />
        <circle cx="260" cy="214" r="150" fill="url(#lp-core)" opacity="0.55" />
        {EDGES.map(([a, b], i) => (
          <line
            key={`${a}-${b}`}
            x1={NODES[a][0]}
            y1={NODES[a][1]}
            x2={NODES[b][0]}
            y2={NODES[b][1]}
            className={`lp-edge${i % 7 === 0 ? " pink" : ""}`}
            style={{ animationDelay: `${(i % 9) * 0.25}s` }}
          />
        ))}
        {NODES.map(([x, y, r], i) => (
          <g key={`${x}-${y}`} className="lp-node" style={{ animationDelay: `${(i % 8) * 0.35}s` }}>
            <circle cx={x} cy={y} r={r + 4} fill={i % 6 === 0 ? "#f472b6" : "#67e8f9"} opacity="0.12" />
            <circle cx={x} cy={y} r={r} fill={i % 6 === 0 ? "#f472b6" : "#67e8f9"} />
          </g>
        ))}
      </svg>
      <div className="lp-float lp-float-a">
        <small>{labels.demo}</small>
        <span>{labels.virality}</span>
        <b>+312%</b>
      </div>
      <div className="lp-float lp-float-b">
        <small>{labels.demo}</small>
        <span>{labels.sentiment}</span>
        <div className="lp-bars" aria-hidden="true">
          {[42, 64, 34, 78, 55, 88].map((h, i) => (
            <i key={h} style={{ height: `${h}%`, animationDelay: `${i * 0.13}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function CountUp({ value }) {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / 900);
      setCurrent(Math.round(value * (1 - (1 - progress) ** 3)));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{current}</>;
}

export default function App() {
  const nav = useNavigate();
  const [lang, setLang] = useState(() => localStorage.getItem("ss_lang") || "tr");
  const [plans, setPlans] = useState(FALLBACK_PLANS);
  const [prompt, setPrompt] = useState("");
  const [typed, setTyped] = useState("");
  const [promptIndex, setPromptIndex] = useState(0);
  const t = COPY[lang] ?? COPY.tr;
  const logged = Boolean(getToken());

  useEffect(() => {
    localStorage.setItem("ss_lang", lang);
    document.documentElement.lang = lang;
    window.dispatchEvent(new CustomEvent("ss_lang_change", { detail: lang }));
    setPromptIndex(0);
    setTyped("");
  }, [lang]);

  useEffect(() => {
    const source = t.prompts[promptIndex % t.prompts.length];
    let index = 0;
    let hold = 0;
    setTyped("");
    const timer = setInterval(() => {
      if (index < source.length) {
        index += 1;
        setTyped(source.slice(0, index));
        return;
      }
      hold += 1;
      if (hold > 42) {
        setPromptIndex((v) => v + 1);
      }
    }, 42);
    return () => clearInterval(timer);
  }, [promptIndex, t.prompts]);

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

  function submitPrompt(event) {
    event.preventDefault();
    const value = prompt.trim();
    if (value) sessionStorage.setItem("ss_prompt", value);
    nav(logged ? "/app/projects/new" : "/register");
  }

  const startHref = logged ? "/app/projects/new" : "/register";
  const panelHref = logged ? "/app" : "/login";

  return (
    <div className="lp">
      <SeoHead
        title={lang === "en" ? "Synthetic community simulation for market research" : "Pazar araştırması için sentetik topluluk simülasyonu"}
        description={lang === "en"
          ? "Simulate how thousands of AI personas react to your campaign before you launch. Synthetic community simulation for market research."
          : "Kampanyanızı yayına almadan binlerce yapay zekâ personasının nasıl tepki vereceğini simüle edin. Pazar araştırması için sentetik topluluk simülasyonu."}
        canonical="/"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          name: "Social Simulator",
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          description: "Sentetik topluluk simülasyonu platformu.",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        }}
      />
      <div className="lp-grid" aria-hidden="true" />
      <div className="lp-glow" aria-hidden="true" />

      <header className="lp-nav">
        <Link className="lp-brand" to="/" aria-label="Social Simulator">
          <img src="/logo-light.png" alt="Social Simulator" />
        </Link>
        <nav className="lp-navlinks" aria-label="Ana menü">
          <a href="#features">{t.navFeatures}</a>
          <a href="#how">{t.navHow}</a>
          <a href="#pricing">{t.navPricing}</a>
          <Link to="/blog">{t.navBlog}</Link>
        </nav>
        <div className="lp-navside">
          <div className="lp-lang" role="group" aria-label="Language">
            <button type="button" className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>en</button>
            <button type="button" className={lang === "tr" ? "active" : ""} onClick={() => setLang("tr")}>tr</button>
          </div>
          <Link className="lp-panel-btn" to={panelHref}>{t.panel}</Link>
        </div>
      </header>

      <main>
        <section className="lp-hero">
          <div className="lp-hero-copy">
            <span className="lp-tag"><i aria-hidden="true" /> {t.heroTag}</span>
            <h1>
              {t.heroA}
              <br />
              <em>{t.heroB}</em>
            </h1>
            <p className="lp-lead">{t.heroSub}</p>

            <form className="lp-prompt" onSubmit={submitPrompt}>
              <span className="lp-prompt-prefix" aria-hidden="true">&gt;</span>
              <div className="lp-prompt-field">
                <input
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  aria-label={lang === "tr" ? "Simülasyon istemi" : "Simulation prompt"}
                />
                {!prompt && (
                  <span className="lp-typed" aria-hidden="true">
                    {typed}<i />
                  </span>
                )}
              </div>
              <button className="lp-prompt-btn" type="submit">{t.promptBtn}</button>
            </form>

            <div className="lp-actions">
              <Link className="lp-btn lp-btn-primary" to={startHref}>{t.cta}</Link>
              <Link className="lp-btn lp-btn-ghost" to={panelHref}>{t.cta2} <span aria-hidden="true">→</span></Link>
            </div>

            <div className="lp-stats">
              {t.stats.map(([value, label]) => (
                <div key={label}>
                  <b>{/^\d+$/.test(value) ? <CountUp value={Number(value)} /> : value}</b>
                  <span>{label}</span>
                </div>
              ))}
            </div>

            <p className="lp-disclaimer">{t.disclaimer}</p>
          </div>
          <NetworkGraph labels={t} />
        </section>

        <section className="lp-section lp-reveal" id="features">
          <div className="lp-section-head">
            <h2>{t.featuresTitle}</h2>
            <p>{t.featuresSub}</p>
          </div>
          <div className="lp-features">
            {t.features.map(([glyph, title, desc]) => (
              <article className="lp-feature" key={title}>
                <span className="lp-feature-icon" aria-hidden="true">{glyph}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="lp-section lp-how lp-reveal" id="how">
          <div className="lp-section-head">
            <h2>{t.howTitle}</h2>
          </div>
          <div className="lp-steps">
            {t.steps.map(([number, title, desc]) => (
              <article className="lp-step" key={number}>
                <span className="lp-step-number">{number}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="lp-section lp-reveal" id="pricing">
          <div className="lp-section-head">
            <h2>{t.pricingTitle}</h2>
            <p>{t.pricingSub}</p>
          </div>
          <div className="lp-plans">
            {plans.map((plan) => {
              const featured = plan.key === "pro";
              return (
                <article className={`lp-plan${featured ? " featured" : ""}`} key={plan.key}>
                  {featured && <span className="lp-plan-tag">{t.popular}</span>}
                  <h3>{planName(plan.key)}</h3>
                  <div className="lp-price">
                    ${plan.price}
                    {plan.price > 0 && <span>{t.perMonth}</span>}
                  </div>
                  <ul>
                    <li><span aria-hidden="true">▸</span> {fmtTokens(plan.token_budget)} {t.tokens}</li>
                    <li><span aria-hidden="true">▸</span> {plan.agents} {t.agents}</li>
                    <li><span aria-hidden="true">▸</span> {plan.rounds} {t.rounds}</li>
                  </ul>
                  <Link className={`lp-plan-btn${featured ? " primary" : ""}`} to={logged ? "/app/billing" : "/register"}>
                    {plan.key === "free" ? t.startFree : t.choose}
                  </Link>
                </article>
              );
            })}
          </div>
          <p className="lp-pricing-note">{t.creditsNote}</p>
          <AdSlot slot="primary" className="ad-slot-inline" />
        </section>

        <section className="lp-final lp-reveal">
          <h2>{t.finalTitle}</h2>
          <Link className="lp-btn lp-btn-primary lp-final-btn" to={startHref}>
            {t.finalCta} <span aria-hidden="true">→</span>
          </Link>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-footer-top">
          <div className="lp-footer-brand">
            <img src="/logo-light.png" alt="Social Simulator" />
            <p>{t.footerNote}</p>
          </div>
          <div className="lp-footer-links">
            <Link to="/blog">Blog</Link>
            <Link to={panelHref}>{t.panel}</Link>
            <Link to={logged ? "/app/billing" : "/register"}>{t.navPricing}</Link>
            <a href="/feed.xml">RSS</a>
            <a href="/llms.txt">llms.txt</a>
            <a href="/sitemap.xml">Sitemap</a>
          </div>
        </div>
        <div className="lp-footer-bottom">
          <span>© {new Date().getFullYear()} Social Simulator</span>
          <span>{t.disclaimer}</span>
        </div>
      </footer>
    </div>
  );
}
