"""Ontology stage: seed docs -> entity/relation types via LLM (task=ingest_ontology)."""
import json


def build_ontology_prompt(seed_summary: str, template_entities: list[str]) -> list[dict]:
    system = (
        "You are a research ontology builder. Given seed material and a set of candidate "
        "entity types, you produce the minimal ontology needed for a community simulation. "
        "Always respond as valid JSON with keys: entity_types (list), relation_types (list), "
        "seed_summary (string <= 2000 chars)."
    )
    user = (
        f"Candidate entity types: {', '.join(template_entities)}\n"
        f"Seed material:\n{seed_summary}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_ontology(raw: str, template, seed_summary: str) -> dict:
    data = None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, dict):
        entity_types = data.get("entity_types")
        relation_types = data.get("relation_types")
        if isinstance(entity_types, list) and entity_types:
            return {
                "entity_types": [str(x) for x in entity_types][:40],
                "relation_types": [str(x) for x in relation_types or template.relation_types][:40],
                "seed_summary": str(data.get("seed_summary") or seed_summary)[:4000],
            }
    return {
        "entity_types": list(template.entity_types),
        "relation_types": list(template.relation_types),
        "seed_summary": seed_summary[:4000],
    }
