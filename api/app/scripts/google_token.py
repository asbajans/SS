"""CLI: OAuth2 authorization code -> refresh token (Google API'leri icin).

Kullanim:
    # 1) authorize URL uretin
    python -m app.scripts.google_token --provider ga4 --client-id <CLIENT_ID>

    # 2) tarayicida acilan URL'ye girin, olusan kodu kopyalayin
    #    (yonlendirme http://localhost:8765/?code=... adresine gider; sayfa
    #     acilmaz, adres cubugundaki code= degerini kopyalayin)
    # 3) refresh token alin
    python -m app.scripts.google_token --provider ga4 --client-id <CLIENT_ID> \
        --client-secret <CLIENT_SECRET> --code 4/0AY...
"""
import argparse

from app.google import oauth_authorize_url, oauth_token_exchange


def main() -> int:
    parser = argparse.ArgumentParser(description="Google OAuth refresh token uret")
    parser.add_argument(
        "--provider",
        required=True,
        choices=["ga4", "search_console", "google_ads", "tag_manager"],
    )
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", default="")
    parser.add_argument("--code", default="", help="authorization code (yoksa sadece URL yazdirilir)")
    # Google, OOB ("urn:ietf:wg:oauth:2.0:oob") akisini kaldirdi; loopback kullanin.
    parser.add_argument("--redirect-uri", default="http://localhost:8765")
    args = parser.parse_args()

    if not args.code:
        url = oauth_authorize_url(args.provider, args.client_id, args.redirect_uri)
        print("Asagidaki URL'yi tarayicida acin ve yetkilendirin:\n")
        print(url)
        print("\nSonra olusan kodu --code ile verin.")
        return 0

    if not args.client_secret:
        print("--client-secret zorunlu", flush=True)
        return 1

    data = oauth_token_exchange(args.client_id, args.client_secret, args.code, args.redirect_uri)
    print("\nRefresh token (panele yapistirin):")
    print(data.get("refresh_token", ""))
    return 0 if data.get("refresh_token") else 1


if __name__ == "__main__":
    raise SystemExit(main())
