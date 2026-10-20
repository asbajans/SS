"""Topic templates (general-community research, not marketing-only)."""
from dataclasses import dataclass, field

PACK_KEYS = (
    "language_default",
    "entity_types",
    "relation_types",
    "persona_fields",
    "action_space",
    "events_enabled",
    "report_outline",
    "sim_defaults",
)


@dataclass
class TopicTemplate:
    key: str
    name: str
    description: str = ""
    language_default: str = "tr"
    entity_types: list[str] = field(default_factory=list)
    relation_types: list[str] = field(default_factory=list)
    persona_fields: list[str] = field(default_factory=list)
    action_space: list[str] = field(default_factory=list)
    events_enabled: bool = True
    report_outline: list[str] = field(default_factory=list)
    sim_defaults: dict = field(default_factory=dict)

    def to_pack(self) -> dict:
        return {
            "language_default": self.language_default,
            "entity_types": list(self.entity_types),
            "relation_types": list(self.relation_types),
            "persona_fields": list(self.persona_fields),
            "action_space": list(self.action_space),
            "events_enabled": self.events_enabled,
            "report_outline": list(self.report_outline),
            "sim_defaults": dict(self.sim_defaults),
        }


MARKET_RESEARCH = TopicTemplate(
    key="market_research",
    name="Pazar Araştırması",
    description="Segmentler, rakipler ve fiyat algısı üzerine sentetik tüketici topluluğu.",
    entity_types=["Segment", "Product", "Competitor", "PricePoint", "Objection", "Trigger"],
    relation_types=["buys", "compares_to", "objects_to", "switches_from"],
    persona_fields=["age", "income_bracket", "usage_level", "choosiness"],
    action_space=["browse", "compare", "cart", "abandon", "objection", "purchase", "recommend"],
    sim_defaults={"agents_n": 80, "rounds": 24, "platforms": 1},
)

PUBLIC_OPINION = TopicTemplate(
    key="public_opinion",
    name="Kamuoyu / Kriz",
    description="Bir mesele etrafında söylem, güven ve yayılım dinamiklerini simüle edin.",
    entity_types=["Actor", "Issue", "Narrative", "Channel", "Sentiment"],
    relation_types=["supports", "opposes", "influences", "echoes"],
    persona_fields=["age_group", "ideology", "media_diet", "prior_knowledge"],
    action_space=["post", "comment", "like", "repost", "mute", "picket", "silent"],
    sim_defaults={"agents_n": 150, "rounds": 40, "platforms": 2},
)

CONCEPT_TEST = TopicTemplate(
    key="concept_test",
    name="Ürün Konsepti",
    description="Özellik önceliklendirme ve JTBD için sanal kullanıcı yorumları.",
    entity_types=["Feature", "JTBD", "Competitor", "Persona", "Price"],
    relation_types=["needs", "prefers", "switches_from"],
    persona_fields=["usage", "skill_level", "budget"],
    action_space=["try", "adopt", "recommend", "ignore", "churn"],
    sim_defaults={"agents_n": 60, "rounds": 20, "platforms": 1},
)

PRICE_PROBE = TopicTemplate(
    key="price_probe",
    name="Fiyat Testi",
    description="Ödeme isteği eğrileri ve fiyat kancası tepkilerini ölçün.",
    entity_types=["Segment", "PriceTier", "CompetitorOffer"],
    relation_types=["accepts", "rejects", "compares"],
    persona_fields=["income_bracket", "price_sensitivity"],
    action_space=["accept", "counter_offer", "abandon"],
    sim_defaults={"agents_n": 100, "rounds": 20, "platforms": 1},
)

POLICY_REVIEW = TopicTemplate(
    key="policy_review",
    name="Politika / Düzenlemeler",
    description="Paydaş tepkileri, destek-itiraz dengesi ve çatışma haritası.",
    entity_types=["Actor", "InterestGroup", "Rule", "Outcome"],
    relation_types=["endorses", "opposes", "lobbies"],
    persona_fields=["stake", "influence", "position_boldness"],
    action_space=["endorse", "oppose", "lobby", "comment", "silent"],
    sim_defaults={"agents_n": 100, "rounds": 30, "platforms": 2},
)

FICTION_REVIEW = TopicTemplate(
    key="fiction_review",
    name="Kültürel / Kurgusal Dünya",
    description="Karakter tutarlılığı, ilişki dinamikleri ve topluluk tepkisi.",
    entity_types=["Character", "Relationship", "Event", "Setting"],
    relation_types=["loves", "betrays", "allies_with"],
    persona_fields=["stance", "fandom_loyalty", "openness"],
    action_space=["write", "comment", "rate", "promote", "spoil_warn"],
    sim_defaults={"agents_n": 50, "rounds": 20, "platforms": 1},
)

_TEMPLATES = [
    MARKET_RESEARCH,
    PUBLIC_OPINION,
    CONCEPT_TEST,
    PRICE_PROBE,
    POLICY_REVIEW,
    FICTION_REVIEW,
]


def get_template(key: str) -> TopicTemplate:
    for t in _TEMPLATES:
        if t.key == key:
            return t
    raise KeyError(f"unknown template: {key}")


def builtin_templates() -> list[TopicTemplate]:
    return list(_TEMPLATES)


def template_from_pack(key: str, name: str, pack: dict, description: str = "") -> TopicTemplate:
    return TopicTemplate(
        key=key,
        name=name,
        description=description,
        language_default=str(pack.get("language_default") or "tr"),
        entity_types=[str(x) for x in (pack.get("entity_types") or [])],
        relation_types=[str(x) for x in (pack.get("relation_types") or [])],
        persona_fields=[str(x) for x in (pack.get("persona_fields") or [])],
        action_space=[str(x) for x in (pack.get("action_space") or [])],
        events_enabled=bool(pack.get("events_enabled", True)),
        report_outline=[str(x) for x in (pack.get("report_outline") or [])],
        sim_defaults=dict(pack.get("sim_defaults") or {}),
    )


def validate_pack(pack: dict) -> str | None:
    if not isinstance(pack, dict):
        return "pack bir JSON nesnesi olmalı"
    for key in ("entity_types", "relation_types", "persona_fields", "action_space"):
        value = pack.get(key)
        if not isinstance(value, list) or not value or not all(isinstance(x, str) for x in value):
            return f"pack.{key}: boş olmayan metin dizisi gerekli"
        if len(value) > 60:
            return f"pack.{key}: en fazla 60 öğe"
    if str(pack.get("language_default") or "tr") not in ("tr", "en"):
        return "pack.language_default: tr veya en olmalı"
    if not isinstance(pack.get("events_enabled", True), bool):
        return "pack.events_enabled: boolean olmalı"
    outline = pack.get("report_outline") or []
    if not isinstance(outline, list) or not all(isinstance(x, str) for x in outline):
        return "pack.report_outline: metin dizisi olmalı"
    defaults = pack.get("sim_defaults") or {}
    if not isinstance(defaults, dict):
        return "pack.sim_defaults: nesne olmalı"
    agents_n = defaults.get("agents_n", 60)
    rounds = defaults.get("rounds", 20)
    platforms = defaults.get("platforms", 1)
    if not isinstance(agents_n, int) or not 1 <= agents_n <= 300:
        return "pack.sim_defaults.agents_n: 1-300 arası tam sayı"
    if not isinstance(rounds, int) or not 1 <= rounds <= 120:
        return "pack.sim_defaults.rounds: 1-120 arası tam sayı"
    if not isinstance(platforms, int) or not 1 <= platforms <= 4:
        return "pack.sim_defaults.platforms: 1-4 arası tam sayı"
    return None


def list_templates() -> list[dict]:
    return [
        {"key": t.key, "name": t.name, "action_space": t.action_space, "sim_defaults": t.sim_defaults}
        for t in _TEMPLATES
    ]
