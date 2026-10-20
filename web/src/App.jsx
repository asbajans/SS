import { Link } from "react-router-dom";

import { TEMPLATES } from "./api.js";
import Icon from "./icons.jsx";

const STEPS = [
  { t: "Kaynakları yükle", d: "Rapor, brief veya metin dosyalarını projeye ekleyin; sistem bilgi tabanını kurar." },
  { t: "Topluluğu simüle et", d: "Yüzlerce sentetik ajan, kişilikleri ve hatıralarıyla forum benzeri ortamda etkileşime girer." },
  { t: "Raporu alın", d: "Olaylara ve belgelere dayalı, simülasyon etiketli detaylı analiz raporu üretin." },
];

export default function App() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="brand">
          <span className="brand-mark">SS</span>
          <span className="brand-name">
            Social Simulation
            <small>topluluk simülasyonu</small>
          </span>
        </div>
        <div className="row">
          <Link className="btn btn-dark btn-sm" to="/login">Giriş</Link>
          <Link className="btn btn-primary btn-sm" to="/register">Ücretsiz Başla</Link>
        </div>
      </nav>

      <header className="landing-hero">
        <span className="hero-tag"><Icon name="users" size={15} /> Sentetik topluluk simülasyonu</span>
        <h1>
          Geleceği tahmin etmek için <em>binlerce ajanı</em> aynı dünyaya yerleştirin
        </h1>
        <p className="lead">
          Konunuzu tanımlayın; sentetik bir topluluk kamuoyu, pazar veya kriz senaryonuzda etkileşime girsin.
          Çıktı: kaynakçalı, denetlenebilir ve{" "}
          <strong style={{ color: "#e8edf7" }}>simülasyon etiketli</strong> raporlar.
        </p>
        <div className="hero-cta">
          <Link className="btn btn-primary" to="/register"><Icon name="play" size={16} /> Simülasyon oluştur</Link>
          <Link className="btn btn-dark" to="/login">Zaten üyeyim</Link>
        </div>
        <div className="hero-stats">
          <div><b>6</b><span>hazır şablon</span></div>
          <div><b>300</b><span>ajana kadar</span></div>
          <div><b>120</b><span>tura kadar derinlik</span></div>
          <div><b>$0,10+</b><span>simülasyon başına</span></div>
        </div>
        <div className="disclaimer-strip">
          Tüm çıktılar simülasyon ürünüdür; gerçek anket veya kamuoyu ölçümü değildir.
        </div>
      </header>

      <section className="landing-section">
        <h2>Altı hazır araştırma şablonu</h2>
        <p className="sub">Konu-agnostik motor; her şablon kendi ontoloji ve aksiyon uzayıyla gelir.</p>
        <div className="feature-grid">
          {TEMPLATES.map((t, i) => (
            <article className="feature" key={t.key}>
              <span className="f-icon" style={{ background: i % 2 === 0 ? "var(--grad)" : "linear-gradient(135deg,#0d9488,#14b8a6)" }}>
                <Icon name="box" />
              </span>
              <h3>{t.name}</h3>
              <p>{t.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section" style={{ paddingTop: 8 }}>
        <h2>Üç adımda topluluk araştırması</h2>
        <p className="sub">Kurulum yok, dış servis yok — her şey yerel altyapıda çalışır.</p>
        <div className="steps-row">
          {STEPS.map((s, i) => (
            <div className="step-card" key={s.t}>
              <span className="n">{i + 1}</span>
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-cta-band">
        <h2>İlk simülasyonunuzu bugün çalıştırın</h2>
        <p>Ücretsiz plan aylık 1M token ile 50 ajanlık simülasyonlara izin verir.</p>
        <Link className="btn btn-primary btn-lg" to="/register">
          <Icon name="arrowLeft" size={16} style={{ transform: "rotate(180deg)" }} /> Hesap oluştur
        </Link>
      </section>

      <footer className="landing-foot">
        <div className="legal">
          <a href="#tos">Kullanım Şartları</a>
          <a href="#privacy">Gizlilik Bildirimi</a>
          <a href="#dmca">DMCA</a>
          <a href="#contact">İletişim</a>
        </div>
        <p>
          Social Simulation — sentetik topluluk simülasyonu platformu. Ajanlar tamamen kurgusaldır;
          gerçek kişisel veri toplanmaz. © {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
}
