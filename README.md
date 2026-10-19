# CrowdScope

Simulated community research SaaS — plan `agent.md` dosyasında.

## Yerel çalıştırma

```bash
cp .env.example .env
docker compose up -d --build
# web:   http://localhost:3900
# api:   http://localhost:3901/docs
# minio: http://localhost:3905 (konsol 3906)
# admin: http://localhost:3910 (Portainer)
```

OpenRouter anahtarı girilmedikçe `LLM_MOCK_MODE=1` varsayılanı ile mock LLM yanıt döner (CI güvenli).

## Deploy (Portainer git stack)

1. Bu repo'yu GitHub'a push edin (ör. `<org>/crowdscope`).
2. Portainer → Stacks → **Add stack → Git repository** → `docker-compose.yml` seçin.
3. Portainer env alanına `.env.example` içindeki değerleri girin (postgres şifresi, Stripe anahtarı, OpenRouter anahtarı).
4. Deploy: web 3900, api 3901.
5. **cloudflared sunucuda zaten kurulu** — ona yeni hostname ekleyin:

```
study.example.com  -> http://localhost:3900
api.example.com    -> http://localhost:3901
admin.example.com  -> http://localhost:3910   (Portainer + Cloudflare Access)
```

## Test

```bash
cd api && ruff check . && pytest
```
