import { Link } from "react-router-dom";

import { TEMPLATES } from "./api.js";
import Icon from "./icons.jsx";

const STEPS = [
  {
    t: "Kaynaklarınızı yükleyin",
    d: "Rapor, brief, haber metni veya senaryo dosyalarınızı projeye ekleyin; sistem bilgi tabanını kurar.",
  },
  {
    t: "Topluluğu simüle edin",
    d: "Yüzlerce sentetik ajan, kişilikleri ve hatıralarıyla forum benzeri ortamlarda etkileşime girer.",
  },
  {
    t: "Kaynakçalı raporu alın",
    d: "Olaylara ve belgelere dayalı, simülasyon ibaresi taşıyan detaylı analiz raporu üretin.",
  },
];

export default function App() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <div className="brand" style={{ padding: 0 }}>
          <span className="brand-mark">CS</span>
          <span className="brand-name">CrowdScope</span>
        </div>
        <div className="row">
          <Link className="btn btn-dark btn-sm" to="/login">Giriş</Link>
          <Link className="btn btn-primary btn-sm" to="/register">Ücretsiz Başla</Link>
        </div>
      </nav>

      <header className="landing-hero">
        <span className="hero-tag">
          <Icon name="users" size={15} /> Sentetik topluluk simülasyonu
        </span>
        <h1>Geleceği kalabalıklarla değil, simülasyonla tahmin edin</h1>
        <p className="lead">
          Konunuzu tanımlayın; binlerce sentetik ajan kamuoyu, pazar veya kriz senaryonuzda
          etkileşime girsin. Sonuç: kaynakçalı, denetlenebilir ve{" "}
          <strong style={{ color: "#f8fafc" }}>simülasyon etiketli</strong> raporlar.
        </p>
        <div className="hero-cta">
          <Link className="btn btn-primary" to="/register">
            <Icon name="play" size={16} /> Simülasyon oluştur
          </Link>
          <Link className="btn btn-dark" to="/login">Zaten üyeyim</Link>
        </div>
        <div className="disclaimer-strip">
          Bu ürünün tüm çıktıları simülasyon ürünüdür; gerçek anket, kamuoyu yoklaması veya
          araştırma ölçümü olarak sunulamaz.
        </div>
      </header>

      <section className="landing-section">
        <h2>Altı hazır araştırma şablonu</h2>
        <p className="sub">Konu-agnostik motor; her şablon kendi ontoloji ve aksiyon uzayıyla gelir.</p>
        <div className="feature-grid">
          {TEMPLATES.map((t) => (
            <article className="feature" key={t.key}>
              <span className="f-icon"><Icon name="box" /></span>
              <h3>{t.name}</h3>
              <p>{t.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section" style={{ paddingTop: 0 }}>
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

      <footer className="landing-foot">
        <div className="legal">
          <span>Kullanım Şartları</span>
          <span>Gizlilik Bildirimi</span>
          <span>DMCA</span>
          <span>İletişim</span>
        </div>
        <p>
          CrowdScope — sentetik topluluk simülasyonu platformu. Ajanlar tamamen kurgusaldır;
          gerçek kişisel veri toplanmaz. © {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
}
