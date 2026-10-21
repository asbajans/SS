# agent.md — Simüle Topluluk Araştırması SaaS

> Çalışma adı: **Social Simulation** (2026-10-20 kararla kesinleşti; önceki kod adı CrowdScope). Şirket: ABD, New Mexico'ya kayıtlı LLC.
> Bu belge: ürün vizyonu, yasal çerçeve (ABD / New Mexico), mimari, veri modeli, pipeline, yol haritası, operasyon ve kabul kriterleri.
> Tek gerçek dış bağımlılık: **OpenRouter**. Diğer her şey kendi konteynerlerinde çalışır.

---

## 1) Ürün tanımı

Kullanıcı bir **konu** (pazar araştırması, kamuoyu/kriz, fiyat testi, özellik önceliklendirme, kültürle/yaratıcı dünya incelemesi) yükler; sistem sentetik bir topluluk (ajan popülasyonu) üretir, ajanlar bir forum ortamında N tur boyunca etkileşir ve sonuçta **kaynakça izli, simülasyon etiketi taşıyan bir rapor** üretilir.

Konu-agnostik çekirdek + **şablon paketleri**. Şablon = `ontology_seed + action_uzayı + persona_prompt + report_template` (bkz. §6). Pazarlama yalnızca ilk şablondur; ürün birden çok "topluluk araştırması" tipi sunar.

**Tabu çizgileri (ürün ilkeyi, hukuki güvenlik için):**
- Gerçek bireylerin kişisel verisi toplanmaz, işlenmez; ajanlar tamamen sentetiktir.
- Raporlar hiçbir koşulda "gerçek anket/gerçek kamuoyu ölçümü" olarak sunulamaz. Her çıktıda sabit ibare: *"Bu rapor bir simülasyon çıktısıdır; gerçek kamuoyu/araştırma ölçümü değildir."*
- Raporlama verisi yalnızca kullanıcının kendi belgeleri + bizim DB'mizdir. Dış web kazıma yok.

---

## 2) Sıfır dışa bağımlılık ilkesi

| Sertifika | Şart |
|---|---|
| DB | PostgreSQL 16 + pgvector (kendi konteyner) |
| Kuyruk | Redis 7 (broker + rate limit + cache) |
| Nesne depolama | MinIO (kendi konteyner) |
| PDF/metin ayıklama | `pypdf` + düz metin (kütüphane, çevrimsiz ağ) |
| Embedding | **TEI** (HuggingFace text-embeddings-inference) + `BAAI/bge-m3` (1024 boy; TR-EN çok dilli). Ağ yok |
| Grafik/Hibrit arama | Postgres içinde: `tsvector` BM25 (tr config) + pgvector kosinüs hibriti; özyinelemeli CTE ile 2 atlamalı geçiş. Zep YOK |
| Kimlik | Kendi AuthFastAPI: Argon2 + JWT |
| Rapor çıktısı | WeasyPrint (PDF; sonraki fazda) + Markdown indirme |
| LLM | **OpenRouter** — tek yetkili dış servis. Yarın Ollama/vLLM'e geçiş aynı Gateway API'si üzerinden mümkün olmalı |

Agresif "0 bağımlılık" tarifi: **kendi erişiş yolu olmadan işleyemeyeceğimiz hiçbir SaaS kullanılmaz.** Kütüphaneler (paket) kabul edilir; SaaS kabul edilmez. Her faz sonunda bu liste gözden geçirilir.

---

## 3) Yasal çerçeve — ABD / New Mexico (2026-10 itibarıyla)

> Not: buradaki bilg bilgi harmanından intibak için yapılmıştır; şirketinizin doğrulanmış avukat ve vergi consultant'ı onayı olmadan transit hukuki belge sayılmaz. Aşağıdaki maddeler **plan** düzeyindedir.

### 3.1 Şirket ve sözleşme
- NM LLC zaten mevcut: tescilli marka, kayıtlı temsilci güncel, Hizmet Adresi + e-posta.
- **ToS**: NM hukuku tabiyet kuralı; uyuşmazlık: AAA arbitrasyon + sınıf davası feragat maddesi; müşteri 18+; TOS metninde açık "simülasyon" tanımı. (Klümel bazlı ülkeler (ABD dışı) tüketiciler için önce coğrafi kısıt; "StackOverflow kararları" gibi vaka listesi ek şablon yorumlarıdır.)
- **Privacy Notice**: kategoriler, amaçlar, kullanıcı hakları, iletişim, veri saklama süreleri — NM kapsamında "hallmark" gibi; metinde "kişisel veri satışı yok, hedefli reklam yok" ifadeleri.

### 3.2 Devlet mevzuatı (New Mexico)
| Yasa | Ne der | Bizde durum / yapılacak |
|---|---|---|
| **NMSA 57-12C — Data Breach Notification Act** | Kabahat bildirimi: NM ikametgâh sakinlerine **45 gün** içinde;NM'de **>1.000** etkilenen varsa **AG + CRA** bildirimi (45 gün içi); tayin 57-12C-9 ile kısmen ertelenir | Breach runbook (§9); bildirim şablonları; AG e-posta listesi; log tablosu (`security_breach_log`) Faz 0'da hazır |
| **UPA (57-12): Unfair Practices Act** | Yanıltıcı/aldatıcı uygulamalar yasa dışı | Her rapor + landing page + reklam metni **simülasyon ibaresi**; "asıl gerçek anket" iddiası yasak; pazarlama metinleri review checklist |
| **GRT (Gross Receipts Tax, NMSA 7-1)** | NM'de "yazılım kullanım lisansı satışı" **mal/hizmet ticareti** sayılır → GRT'ye tabi (NMAC 3.2.1.27). Fizikisel varlık yoksa $100k NM-sourced eşiği (NMSA 7-1-7/23) | SaaS (subscription) müşteri konumu bazlı raporlama: FYI-200 (lokasyon kodu) + FYI-206 okunur; müşteri adresi toplandığı için location bazlı fatura (Stripe'ta tax_id + address zorunlu). **Vergi danışmanına: B2B dışarıya satış (NTTC 7-9-57 çıkarımı) olasılığı ve B2C NM müşterilerde GRT'nin ayrıca gösterilip gösterilmeyeceği** karar verilecek. NMSA-1 online tescil |
| **HB410 (Consumer Information & Data Protection Act)** | 2025 oturumunda komitede **kabul edilmedi (postponed indefinitely, Haziran 2025)** — NM'de şu an **kapsamlı tüketici gizliliği yasası yok**. 2026–2028 oturumlarında benzeri beklenir | Proaktif uyum: NIST CSF-lite güvenlik, DSR formu, veri envanteri — yasa gelirse hazır. GDPR benzeri gereksinim hazırlığı Faz 4'te |
| **Colorado SB26-189 ADMT Act** (2027-01-01) | Yalnız "Consequential Decision" (işe alım, kredi, sağlık, konut vb.) veren sistemler | Ürün **hiber kernel dışı** (insan hakkında consequential decision üretmiyor), yine de 2026-Q4'te tekrar değerlendirilecek (watchlist) |
| Federal | FTC §5 (deceptive), CAN-SPAM, COPPA (<13 yasak; biz zaten 18+ gate), DMCA safe harbor (kullanıcı yüklemesi için agent designation + takedown süreci, repeat-infringer policy) | Faz 0'da takedown süreci sayfası; DAMCA agent tescil (copyright.gov); CAN-SPAM uyumlu transactional/marketing ayrımı |

### 3.3 Ödeme: **Stripe**
- Stripe Billing: **abonelik (subscription) + usage-based (token credit)** kombinasyonu.
- Webhook tabanlı plan senkronizasyonu. Webhook Secret: Portainer secrets.
- Faturada satıcının VKN/EIN, müşteri fatura adresi (GRT lokasyonu için) zorunlu alan.
- Geri ödeme politikası TOS'ta: 1. ay **iade yok** (token sarfı geri alınamaz) ya da pro-rata kredisi — karar Faz 5'te, ToS'ta net yazılır.
- OFAC/sanctions screen: Stripe adaptive checks + country block list (yorumlanır listeyi ayarla).

### 3.4 Veri çeşitliliği & KVKK/GDPR konumu
- Ana hedef pazar: **Türkiye + global (İngilizce)**. TR kullanıcıları için GDPR/KVKK eşdeğeri metin hazırlanacak (Avrupa sınırlamaları: Faz 5'te "GDPR-ready" olmadan EU-EEA kaydı coğrafi kısıtla kapalı tutulabilir).
- Veri sınıflandırması:
  - **Kişisel veri** ( bizde): email, hashli şifre, fatura metadata, usage log. Kategorileri Privacy Notice'ta listele.
  - **İş verisi**: kullanıcı belgeleri, ontoloji, ajan, olay kaydı, rapor.
  - **Sentetik veri**: ajan postları. Tamamen ürün çıktısı, müşterilere aittir (ToS'ta mülkiyet).
- **Veri unutma**: DSR endpoint `POST /privacy/requests` + otomatik ISO silme akışı (kullanıcı siler → DB rows + MinIO objects + PDF + token log'ları anonimleştir) Faz 4.

---

## 4) Mimari (Portainer + önceden kurulu Cloudflare Tunnel, port bandı 3900–3950)

```
study.domain.com ── ingress (web)        ─┐
api.domain.com  ─── ingress (api)         ├─→ sunucudaki mevcut cloudflared (stack dışı)
admin.domain.com ── Tunnel + Access (ops) ─┘
```

**Port tablosu:**

| Host port | Servis | Erişim |
|---|---|---|
| 3900 | web (nginx/SPA) | Public (tunnel) |
| 3901 | api (FastAPI) | Public (tunnel) |
| 3902 | REZERVE (belki PDF servisi) | — |
| 3903 | postgres+pgvector | 127.0.0.1 |
| 3904 | redis | 127.0.0.1 |
| 3905 / 3906 | MinIO API / Konsol | 127.0.0.1 |
| 3907 | TEI (bge-m3) | 127.0.0.1 |
| 3910 | Portainer (dışarıda, tunnel+Access) | Public (access) |
| 3920–3922 | Grafana / Prometheus / Loki (Faz 4) | 127.0.0.1 |
| 3923–3950 | REZERVE (gelecek: model + yeni worker yönlendirme) | — |

**Yayılma şekli:** monorepo GitHub → **Portainer "Git repository stack"** → compose otomatik deploy → `--prune`. Secrets `.env` ile Portainer "env" alanından sağlanır (repo'ya secret girilmez).

**Çekirdek kapsayıcılar:**
- `web` (nginx, SPA + `/api` proxy api:8000'e)
- `api` (FastAPI; aynı image worker için yeniden kullanılır)
- `worker` (Celery; command override)
- `db`, `redis`, `minio`, `minio-init`, `tei`, `backup`
- (Faz 4): `grafana`, `prometheus`, `loki`

**cloudflared stack dışındadır** (sunucuda zaten çalışıyor). Yeni hostname'ler Zero Trust → Tunnels → Public Hostname olarak eşlenir: `study → http://localhost:3900`, `api → http://localhost:3901`, `admin → http://localhost:3910`.

"Zero-dependency" kontrol noktası: `docker compose ps` → tüm kritik servis lokal Ağ; dışa giden sadece `cloudflared` + `api→openrouter.ai` + `api→stripe.com`.

---

## 5) LLM Altyapısı: OpenRouter Gateway (arka planda limitli model seçimi)

### 5.1 Görev tanımlı model haritası (admin CRUD)
DB tablosu `model_configs` ile **her görev ayrı konfigüre edilir**:

```json
{ "task_key": "agent_act",        "model": "meta-llama/llama-3.1-8b-instruct",
  "max_tokens": 700,  "temperature": 0.7, "rpm": 120, "daily_token_budget": 3000000,
  "fallbacks": ["openai/gpt-4o-mini"],
  "cost_in_usd_per_mtok": 0.05, "cost_out_usd_per_mtok": 0.25 }
```

Varsayılan görev anahtarları:

| task_key | Amaç | Önerilen varsayılan model sınıfı |
|---|---|---|
| `ingest_ontology` | Belge toplu → ontoloji | strong (`anthropic/claude-sonnet-4` veya `openai/gpt-5-medium`) |
| `persona_synth` | Popülasyon sentezi (5 kişilik batch) | orta (`google/gemini-2.5-flash`, `meta-llama/llama-3.1-70b-instruct`) |
| `agent_act` | Ajan aksiyon kararları (döngü — en ağır) | ucuz (`llama-3.1-8b-instruct`) |
| `agent_digest` | Ajan hafıza özetleri (her 5 tur) | ucuz |
| `analyst_draft` | Rapor alt-sorgu/outline | orta/güçlü |
| `report_section` | Rapor bölümü ReACT | güçlü |
| `agent_interview` | Rapor üretiminde ajan derinlemesine soru-cevap | orta |

### 5.2 Gateway akışı (api/app/llm_gateway/gateway.py)
1. `resolve_config(task_key)` → DB'den (30 sn TTL önbellek) + admin invalidasyon.
2. **Kota kontrolü:** kullanıcı aylık token bütçesi (plan bazlı) + görev günlük bütçesi + `OPENROUTER_MONTHLY_CAP_USD` (hesap geneli harcama limiti OpenRouter panelinde ayrıca ayarlanır).
3. **Token bucket** rate limit: Redis `rl:{task}` (rpm, tpm). 
4. `max_tokens` **zorunlu** (sınırsız çıktı = hata). `usage: {include: true}` parametresi ile gerçek token + maliyet döner.
5. **Fallback zinciri:** ana model fail/timeout/429/5xx → sıradaki model; hepsi başarısızsa `TaskError` → iş "token harcanmamış" işaretlenir, kullanıcıya kredi iade.
6. **Usage kaydı:** `token_usage` tablosuna `prompt_tokens, completion_tokens, cost_usd, model, task, project_id, run_id, agent_id, seq` yazılır → Bu tablo, ürünün gerçek maliyet temel çizgisidir (Faz 1 çıkışı: bir sim maliyet profil).
7. `response_format: json_object` yerine "şemalı prompt + parse + tek retry" stratejisi (tüm sağlayıcılar response_format'ı güvenilir desteklemiyor).
8. **Mock mod:** `OPENROUTER_API_KEY` boşsa veya `LLM_MOCK_MODE=1` → tenezzülsüz kaba yanıt üretir (test/CI); maliyet 0.

---

## 6) Konu Şablon Kütüphanesi (yalnız pazarlama değil)

| Şablon | Ontoloji çekirdeği | Aksiyon uzayı | Rapor çıktısı |
|---|---|---|---|
| `market_research` | Segment, Ürün, Rakip, Fiyat Noktası, İtiraz | browse, compare, cart, abandon, objection, purchase | TAM/SAM/SOM, niyet skoru, esneklik, itiraz haritası |
| `public_opinion` | Aktör, Mesele, Söylem, Kanal | post, like, repost, mute, picket | görünüm eğrisi, güven skoru, salgın eşiği |
| `concept_test` | Özellik, JTBD, Rakip, Fiyat | deneme, tavsiye, kaydetim | özellik öncelik matrisi |
| `price_probe` | Segman, Fiyat Kancası | kabul, sahiplenme, karşı teklif | WTP eğrisi, gelir simülasyonu |
| `policy_review` | Aktör, İlgi grubu, Kural | destekle, itiraz, görüş | kabul eğrisi, çatışma haritası |
| `fiction_review` | Karakter, İlişki, Olay | yaz, yorum, taraftar | tutarlılık raporu |

Şablon paketi JSON (Python dataclass'la eşleşir): `schema_version, ontology_seed, actions, persona_prompt_hint, report_template, sim_default_config`. Admin "şablon ver" UI Faz 4; MVP'de 2 şablon (market_research, public_opinion) kod içinde.

**Rapor Ajanı**: Sadece **kendi DB + kullanıcı belge**lerine sorgu yapabilir (4 araç: `search_docs`, `query_events`, `get_aggregate`, `interview_agent`). Dış web yok. ReACT: outline → bölüm → her bölümle `analyst_draft + report_section` çağrıları.

---

## 7) Veri modeli (db/init.sql)

| tablo | açıklama |
|---|---|
| `users` | id, email(Argon2 hashli pw), plan, monthly_token_used, is_admin, created_at |
| `model_configs` | task_key PK, model, fallbacks, max_tokens, temperature, rpm, tpm, daily_budget, monthly_budget, cost_in/out_usd_per_mtok, enabled |
| `projects` | id, user_id, name, template_key, language, status, config jsonb |
| `documents` | id, project_id, filename, minio_key, mime, size, sha256 |
| `document_chunks` | id, document_id, chunk_idx, content, embedding vector(1024), tsv tsvector |
| `ontologies` | id, project_id, entity_types jsonb, relation_types jsonb, seed_summary |
| `agents` | id, project_id, agent_idx, name, bio, persona, memory text |
| `runs` | id, project_id, status, sim_config jsonb, started_at, finished_at, token_budget, tokens_used, report_key |
| `run_events` | id BIGSERIAL, run_id, seq, agent_id, seq_in_round, round, event_type, payload jsonb, created_at |
| `token_usage` | id, user_id, project_id, run_id, task_key, model, prompt_tokens, completion_tokens, cost_usd, meta jsonb, created_at |

İndeksler: `document_chunks.embedding` (ivfflat, lists=100), `document_chunks.tsv` (GIN), `run_events(run_id, seq)`, `token_usage(created_at)`, `agents(project_id)`.

---

## 8) Pipeline (Celery task: `app.tasks.pipeline.run_pipeline`)

```
created
 └─ ingesting   → download docs from MinIO → pypdf/text → chunk → TEI embed → pgvector
 └─ ontology    → 1 LLM çağrısı (analyst) → entity/relation şemaları
 └─ population  → persona_synth (batch 5) → N ajan (DB agents)
 └─ running     → scheduler loop:
                   for round R:
                     for each of P platforms (şablon'dan forum sayısı):
                       active = sample(agents, uniform(min,max) × hour_multiplier)
                       for agent in active (semaphore'lı eşzamanlılık faz 2'de):
                          action = gateway(agent_act, persona + son 15 olay + şablon yönergesi)
                          write run_events
                     every K rounds → agent_digest (hafıza özeti)
 └─ report      → report_outline → report_section (ReACT; araçlar yerel DB)
 └─ report_md → MinIO + run.report_key; status=completed
```

Zaman/sim konfigürasyonu (`run.sim_config`): `agents_n, rounds, platforms, peak_hours, off_peak_hours, agents_per_hour_min/max, activity_level, digest_every, max_tokens_per_round`. Bu değerler proje sihirbazında şablon varsayılanlarından gelir; kullanıcı seçtiği **Hızlı/Standart/Derin** profiliyle sabitlenir:

| Profil | N | R | P | ≈Token | ≈Maliyet (llama-8b/gpt-4o-mini mix) |
|---|---|---|---|---|---|
| Hızlı | 80 | 24 | 1 | 1.6 M | ~$0.10–0.35 |
| Standart | 150 | 40 | 2 | 6.6 M | ~$0.45–1.40 |
| Derin | 250 | 72 | 2 | 17.3 M | ~$1.15–3.60 |

(Bunlar kod-türevli tahminler; Faz 1 çıkışı: gerçek `token_usage` ölçümüyle aşağıdaki tablo güncellenecek.)

---

## 9) Güvenlik & Operasyon

- **Sırlar:** `.env` (Portainer env). Repo'da `.env.example` hariç secret YOK. `OPENROUTER_MONTHLY_CAP_USD` ile OpenRouter hesap genelli harcama tavanı ayarlanır. Stripe webhook + sinyal. Cloudflare Access ile `api.domain.com/admin/*` ve Portainer korunur.
- **Backups:** compose içinde `backup` servisi (`postgres-backup-local`) günlük `pg_dump` üretir; retansiyon 30 gün. Uzak S3 hedefi Faz 4'te eklenir.
- **Loglama:** `structlog` JSON; her LLM çağrısının `trace_id`'si `token_usage.meta` içinde.
- **Breach runbook:** alarm → triyaj (57-12C-6 45 gün), NM AG + CRA (>1.000 kişi), kullanıcı bildirimi; `security_breach_log`. Drill Faz 4.
- **CI:** GitHub Actions → ruff + pytest (mock LLM) + `docker build` (api, web). Failing build Portainer'a deploy edilmez.
- **Versiyonlama:** semver; compose name `crowdscope`.

---

## 10) Yol haritası

| Faz | Hafta | Çıktı | Kabul kriterleri (DoD) |
|---|---|---|---|
| **F0 — Hukuk + mimari** | 1. | ToS/Privacy taslağı hazır (avukat onayına açık), repo iskeleti, compose yukarda çalışıyor | `docker compose up` tüm servisleri green; Cloudflare tunnel çalışıyor; `.env.example` eksiksiz |
| **F1 — Omurga** | 2–3 | Auth (register/login, admin ilk kullanıcı), LLMGateway (kota + limit + fallback + `token_usage`), admin model CRUD, health, Stripe checkout/webhook iskelet. | Mock modda `agent_act` 10.000 çağrı üretilip token sayımları doğru; admin panelde model limiti değiştirilince davranış değişmektedir |
| **F2 — Motor MVP** | 4–7 | 2 şablon: ingest → ontoloji → population → scheduler → run_events → SSE status | 150 ajan × 40 tur sim, gerçek OpenRouter anahtarıyla, token derin profili ölçümlü |
| **F3 — Rapor** | 8–9 | Rapor Ajanı: outline → sections → Markdown + (WeasyPrint PDF) | Kaynakça izli rapor + sim disclaimers + MinIO'dan indirilebilir |
| **F4 — Çoklu konu + admin + GDPR** | 10–11 | Şablon UI, grafana/loki, DSR silme, backup cron | Yeni şablon yüklenip aynı pipeline çalışıyor; Silme talebi 7 gün içinde tam uygulanır |
| **F5 — Ticari açılış** | 12–13 | Iyzico değil **Stripe** abonelik + Usage credit; landing/pricing; TR/EN UI; ölçekleme | İlk 10 ödeme tasarımının yıldız testi: kullanıcının signup→ücretli rapor indirme akışı |
| **F6 - Rapor kütüphanesi** | 14 | Tamamlanan raporların listesi, arama, PDF/MD indirme; `report_ready` alanı | Kullanıcı tüm raporlarını tek ekranda görür, arama yapar ve PDF/MD indirir; boş durum yönlendirmesi çalışır |
| **F7 - Pazarlama sitesi** | 15 | Public blog (TR/EN), landing animasyonları, blog navigasyonu | `/blog` ve `/blog/{slug}` yayında; landing'de blog linki, reveal animasyonları ve prefers-reduced-motion desteği |
| **F8 - API platformu** | 16 | API anahtarları, `/api/v1` proje/run/rapor uçları, HMAC imzalı webhook'lar, geliştirici UI | Anahtar ile proje oluşturup run başlatma ve rapor indirme uçtan uca çalışır; webhook imzası doğrulanır, SSRF engellenir |
| **F9 - Görüş analizi + içerik** | 17 | Görüş/karar dağılımı, neden temaları ve grafikli rapor analizi; `social_post_test` senaryosu; AI blog editörü + zamanlanmış yayın; müşteri arayüzünde maliyet gizleme | Müşteri maliyet görmez; rapor ekranı olumlu/olumsuz/kararsız yüzdelerini, gerekçeleri ve yorumları gösterir; hazır gönderi hedef kitleye test edilir; admin konu kuyruğu ve otomatik yayın aralığını yönetir |

Kaynak: 1 dev tam zamanlı + 1 UI/barkı → ~13 hafta; 2 dev → ~10–14 hafta.

Sunucu önerisi: 8 vCPU / 32 GB RAM / 200 GB SSD (TEI ~4–8 GB RAM; ajan aksiyonu CPU'da değil OpenRouter'da ağırlıklı; throttling Gateway'de).

---

## 11) Riskler & mitigasyonlar

| Risk | Etki | Mitigasyon |
|---|---|---|
| OpenRouter tek-nokta bağımlılık | Yüksek | Fallback zinciri (Gateway §5.2); ileride Ollama/vLLM'de aynı API ile yedek sağlayıcı; OPENROUTER_MONTHLY_CAP_USD |
| LLM out-of-budget (akılsız üretim) | Kâr marjı | `max_tokens` zorunlu, task bazlı bütçe, profil Hızlı/Standart/Derin, gerçek ölçüm Faz 1 |
| AGPL suçlaması | Yüksek | Temiz-oda ilkesi: MiroFish kodu **kopyalanmaz**; sadece OASIS (Apache-2.0) kavramsal referans; ayrı repo |
| Simülasyon bilimsel geçerlilik | Kritik | Her raporda disclaimers; gerçek anket/focus group ile korelasyon çalışması (Faz 6+); sonuçlar 95% güven aralığı içi sinyallerle sunulur |
| KVKK/CRM abonelik iptali | Orta | Stripe webhooks + cancel at period end; DSR süreci Faz 4 |
| NM GRT dosyalama hatası | Orta | Vergi danışmanı ile Faz 5'te; System rapor otomasyonu (aylık GRT raporu); NTTC B2B dışarı satış ayrımı |

---

## 12) Repo şablonu (bu belgeyle birlikte oluşturuldu)

```
socialcommunity/
├── agent.md                 ← bu dosya
├── docker-compose.yml       ← Portainer Git stack ile deploy edilir
├── .env.example
├── db/init.sql              ← şema v1
├── api/ (FastAPI + SQLAlchemy + Celery; worker aynı image)
│   ├── Dockerfile, pyproject.toml
│   ├── app/ (main, config, security, routers/, llm_gateway/, tasks/, integrations/)
│   └── tests/
├── engine/ (konu-agnostik simülasyon motoru; api image'ına gömülür)
├── web/ (Vite + React + nginx)
├── ops/backup/
└── .github/workflows/ci.yml
```

Deploy akışı:
1. GitHub repo aç → bu klasörü push (özel repo; secrets repoda saklanmaz).
2. Portainer → Stacks → **Add stack → Git repository** → repo URL + branch + `docker-compose.yml` path.
3. Portainer "Environment variables" alanına `.env.example` içindeki tüm değerleri gir.
4. Deploy → Portainer UI 3910 (önceden kurulu), web 3900, api 3901.
5. Mevcut cloudflared yapılandırmasına hostname ekleyin: `study.example.com → http://localhost:3900`, `api.example.com → http://localhost:3901`, `admin.example.com → http://localhost:3910` (+ Access policy).

---

## 13) Karar günlüğü

- 2026-10-19: Plan v1. AGPL'den temiz-oda seçildi; OpenRouter tek harici servis; lisans/konum NM bazlı ToS.
- 2026-10-19 (rev): cloudflared stackten çıkarıldı (sunucuda zaten kurulu); port bandı 3900–3950'e taşındı.


---

## 14) Web arayuz tasarim sistemi (F10)

- Tasarim dili: Lovable referans tasarimi (twinworld-social-simulator.lovable.app) temel alindi; koyu lacivert zemin, cam (glass) kartlar, cyan-pink neon vurgu, Orbitron baslik + Space Grotesk govde + JetBrains Mono etiket.
- Dosyalar: web/src/landing.css (landing sayfasi, .lp-* siniflari), web/src/theme.css (panel/blog koyu tema tokenlari ve component override'lari), web/src/styles.css (temel primitifler).
- Fontlar Google Fonts uzerinden: Orbitron, Space Grotesk, JetBrains Mono.
- Marka varliklari: kok dizindeki logo.jpg, icon.jpg, icon.ico -> web/public/logo-light.png, web/public/logo.png, web/public/icon-mark.png, web/public/icon-192.png, web/public/icon.ico (beyaz arka plan saydamlastirildi). Favicon: icon.ico.
- Landing sayfasi tek sayfadir: hem socialsimulator.com.tr hem app.socialsimulator.com.tr kok yolunda ayni SPA acilir; panel /app altindadir. Yeni host icin yeni port gerekmez: cloudflared Public Hostname olarak socialsimulator.com.tr -> http://localhost:3900 eklenir (web nginx /api isteklerini api:8000 konteynerine proxy'ler).
- Landing istem kutusu sessionStorage.ss_prompt ile giris/kayit sonrasi /app/projects/new sayfasina proje adi + brief olarak aktarilir.
---

## 15) Google ile giris (GIS ID token)

- Akis: SPA -> Google Identity Services butonu -> `POST /api/auth/google` (ID token JWT) -> API imzayi Google JWKS ile dogrular (RS256, aud = client id, iss = accounts.google.com, email_verified) -> kullaniciyi olusturur/eskisiyle birlestirir -> kendi JWT'mizi dondurur.
- Client secret gerekmez (public client, sadece client id). `GOOGLE_CLIENT_ID` env degiskeni virgulle ayrilmis birden fazla id destekler.
- Dosyalar: `api/app/google_auth.py` (dogrulama), `api/app/auth.py` (`GET /api/auth/google/config`, `POST /api/auth/google`), `web/src/google.js` (GIS script yukleyici), `web/src/components/GoogleAuth.jsx` (buton), `api/tests/test_google_auth.py`.
- Veritabani: `users.google_id` kolonu (nullable, unique) - `startup.py` migration + `db/init.sql`.
- Kapaliysa `GET /api/auth/google/config` -> `{enabled:false}` ve arayuzde buton gorunmez; `POST` 403 yerine 503 doner.- Google Identity Services (OAuth 2.0, ID token) ek bir SaaS olarak 2026-10-21 onaylandi; client secret kullanilmaz, sadece `GOOGLE_CLIENT_ID` (public client id) env degiskeni. Dogrulama: RS256 JWKS (cryptography paketi) + tokeninfo yedegi.
---

## 16) Panel i18n (TR/EN)

- `web/src/dict.js`: TR -> EN sozluk (390+ girdi; tum panel metinleri, tablo basliklari, sablon adlari/aciklamalari, durumlar).
- `web/src/i18n.js`: runtime ceviri. `ss_lang` localStorage anahtari; `initI18n()` DOM'u gezer, metin dugumlerini ve `placeholder`/`title` niteliklerini sozlukle degistirir; MutationObserver ile React yeniden render oldugunda tekrar uygular; `setLang()` ceviriyi geri alir (TR'ye donus). `document.documentElement.lang` EN/TR olarak guncellenir (CSS uppercase Turkce locale sorunu).
- Panelde TR/EN anahtari topbar'da (`lang-pill`); landing (`App.jsx`) ve blog sayfalari ayni `ss_lang` degerini paylasir.
- Yeni proje olustururken rapor dili secimi `ss_lang` degerinden baslar.
- Not: API'den gelen veri (proje adi, blog yazi basligi, kullanici e-postasi) cevrilmez; yalnizca arayuz metinleri cevrilir.