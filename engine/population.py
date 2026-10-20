"""Synthetic population builders (persona batches of 5, clean implementation)."""
import json
import random

PERSONA_HINTS = {
    "market_research": {
        "demography": "Age, income, shopping channel preference, brand loyalty.",
        "hint": "Include buying triggers and objections.",
    },
    "public_opinion": {
        "demography": "Age group, ideology, media diet, prior knowledge of topic.",
        "hint": "Include how much they trust institutions and each other.",
    },
    "concept_test": {
        "demography": "Usage habits, skill level, budget.",
        "hint": "Include adoption barriers and motivation.",
    },
    "price_probe": {
        "demography": "Income bracket, price sensitivity, alternative offers.",
        "hint": "Include willingness-to-pay anchors.",
    },
    "policy_review": {
        "demography": "Stake, influence, position boldness.",
        "hint": "Include affected groups and coalition leanings.",
    },
    "fiction_review": {
        "demography": "Stance, fandom loyalty, openness.",
        "hint": "Include favorite character dynamics.",
    },
}

_FIRST = [
    "Elif", "Mehmet", "Zeynep", "Ahmet", "Defne", "Burak", "Selin", "Can", "Ayşe",
    "Emre", "Merve", "Onur", "Ece", "Kerem", "İrem", "Deniz", "Cem", "Buse",
    "Kaan", "Sıla", "Tolga", "Nazlı", "Barış", "Pelin", "Serkan", "Derya", "Umut",
    "Gizem", "Arda", "Yasemin", "Okan", "Melis", "Hakan", "Sevgi", "Levent", "Nur",
]
_LAST = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Aydın", "Öztürk",
         "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara", "Koç", "Kurt", "Özkan"]
_TRUST = ["düşük", "orta", "yüksek"]
_ATTITUDE = ["temkinli", "meraklı", "eleştirel", "destekleyici", "kararsız"]


def build_persona_prompt(
    template, language: str, count: int, start_idx: int, seed_summary: str
) -> list[dict]:
    fields = ", ".join(template.persona_fields)
    hints = PERSONA_HINTS.get(template.key, {})
    system = (
        "You generate diverse synthetic research personas for a community simulation. "
        "Respond as strict JSON with key personas: a list. Each persona must have "
        "name, bio (1-2 sentences), persona (demographics, attitudes, motivations), "
        "platform, and attributes (object keyed exactly by the requested field names). "
        "Never use real people's names or hallmarks of real identities. "
        f"Write all text in language '{language}'."
    )
    user = (
        f"Template: {template.name} ({template.key})\n"
        f"Requested persona fields: {fields}\n"
        f"Extra hints: {hints.get('demography', '')} {hints.get('hint', '')}\n"
        f"Start index: {start_idx}\n"
        f"Count: {count}\n"
        f"Seed material:\n{seed_summary[:2500]}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _synthetic(idx: int, template, rng: random.Random, language: str) -> dict:
    first = rng.choice(_FIRST)
    last = rng.choice(_LAST)
    name = f"{first} {last}"
    attitude = rng.choice(_ATTITUDE)
    trust = rng.choice(_TRUST)
    attributes = {}
    for field in template.persona_fields:
        key = field.lower()
        if "age" in key or "yaş" in key:
            attributes[field] = rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"])
        elif "income" in key or "gelir" in key or "budget" in key:
            attributes[field] = rng.choice(["düşük", "orta", "yüksek"])
        elif "ideology" in key:
            attributes[field] = rng.choice(["merkez", "muhafazakâr", "liberal", "apolitik"])
        elif "media" in key:
            attributes[field] = rng.choice(["sosyal medya", "TV", "gazete", "podcast"])
        elif "trust" in key or "güven" in key:
            attributes[field] = trust
        elif "stance" in key or "position" in key:
            attributes[field] = attitude
        elif "loyalty" in key:
            attributes[field] = rng.choice(["düşük", "orta", "yüksek"])
        elif "usage" in key or "kullanım" in key:
            attributes[field] = rng.choice(["yeni", "düzenli", "ağır"])
        elif "sensitivity" in key or "hassasiyet" in key:
            attributes[field] = rng.choice(["düşük", "orta", "yüksek"])
        elif "influence" in key or "etki" in key:
            attributes[field] = rng.choice(["düşük", "orta", "yüksek"])
        else:
            attributes[field] = rng.choice(["düşük", "orta", "yüksek"])
    bio = (
        f"{idx}. sentetik katılımcı: {template.name.lower()} konusunda {attitude} bir tutum sergiliyor. "
        f"Kurumlara güveni {trust} düzeyinde."
    )
    persona = (
        f"{name}; {', '.join(f'{k}={v}' for k, v in attributes.items())}. "
        f"Sentetik topluluk simülasyonu için üretilmiş bir personalardır."
    )
    return {
        "name": name,
        "bio": bio,
        "persona": persona,
        "attributes": attributes,
        "platform": rng.choice(["forum", "social", "news"]),
    }


def parse_personas(
    raw: str, template, count: int, start_idx: int, language: str = "tr"
) -> list[dict]:
    data = None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, dict):
        data = data.get("personas")
    out: list[dict] = []
    if isinstance(data, list):
        for item in data[:count]:
            if not isinstance(item, dict):
                continue
            attributes = item.get("attributes")
            out.append(
                {
                    "name": str(item.get("name") or f"Agent {start_idx + len(out)}")[:120],
                    "bio": str(item.get("bio") or "")[:2000] or None,
                    "persona": str(item.get("persona") or item.get("bio") or "")[:4000] or None,
                    "attributes": attributes if isinstance(attributes, dict) else {},
                    "platform": str(item.get("platform") or "forum")[:32],
                }
            )
    rng = random.Random(4200 + start_idx)
    for _ in range(count - len(out)):
        out.append(_synthetic(start_idx + len(out), template, rng, language))
    return out[:count]
