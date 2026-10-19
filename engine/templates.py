"""Topic templates (general-community research, not marketing-only)."""
from dataclasses import dataclass, field


@dataclass
class TopicTemplate:
    key: str
    name: str
    language_default: str = "tr"
    entity_types: list[str] = field(default_factory=list)
    relation_types: list[str] = field(default_factory=list)
    persona_fields: list[str] = field(default_factory=list)
    action_space: list[str] = field(default_factory=list)
    events_enabled: bool = True
    report_outline: list[str] = field(default_factory=list)
    sim_defaults: dict = field(default_factory=dict)


MARKET_RESEARCH = TopicTemplate(
    key="market_research",
    name="Pazar Araştırması",
    entity_types=["Segment", "Product", "Competitor", "PricePoint", "Objection", "Trigger"],
    relation_types=["buys", "compares_to", "objects_to", "switches_from"],
    persona_fields=["age", "income_bracket", "usage_level", "choosiness"],
    action_space=["browse", "compare", "cart", "abandon", "objection", "purchase", "recommend"],
    sim_defaults={"agents_n": 80, "rounds": 24, "platforms": 1},
)

PUBLIC_OPINION = TopicTemplate(
    key="public_opinion",
    name="Kamuoyu / Kriz",
    entity_types=["Actor", "Issue", "Narrative", "Channel", "Sentiment"],
    relation_types=["supports", "opposes", "influences", "echoes"],
    persona_fields=["age_group", "ideology", "media_diet", "prior_knowledge"],
    action_space=["post", "comment", "like", "repost", "mute", "picket", "silent"],
    sim_defaults={"agents_n": 150, "rounds": 40, "platforms": 2},
)

CONCEPT_TEST = TopicTemplate(
    key="concept_test",
    name="Ürün Konsepti",
    entity_types=["Feature", "JTBD", "Competitor", "Persona", "Price"],
    relation_types=["needs", "prefers", "switches_from"],
    persona_fields=["usage", "skill_level", "budget"],
    action_space=["try", "adopt", "recommend", "ignore", "churn"],
    sim_defaults={"agents_n": 60, "rounds": 20, "platforms": 1},
)

PRICE_PROBE = TopicTemplate(
    key="price_probe",
    name="Fiyat Testi",
    entity_types=["Segment", "PriceTier", "CompetitorOffer"],
    relation_types=["accepts", "rejects", "compares"],
    persona_fields=["income_bracket", "price_sensitivity"],
    action_space=["accept", "counter_offer", "abandon"],
    sim_defaults={"agents_n": 100, "rounds": 20, "platforms": 1},
)

POLICY_REVIEW = TopicTemplate(
    key="policy_review",
    name="Politika / Düzenlemeler",
    entity_types=["Actor", "InterestGroup", "Rule", "Outcome"],
    relation_types=["endorses", "opposes", "lobbies"],
    persona_fields=["stake", "influence", "position_boldness"],
    action_space=["endorse", "oppose", "lobby", "comment", "silent"],
    sim_defaults={"agents_n": 100, "rounds": 30, "platforms": 2},
)

FICTION_REVIEW = TopicTemplate(
    key="fiction_review",
    name="Kültürel / Kurgusal Dünya",
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


def list_templates() -> list[dict]:
    return [
        {"key": t.key, "name": t.name, "action_space": t.action_space, "sim_defaults": t.sim_defaults}
        for t in _TEMPLATES
    ]
