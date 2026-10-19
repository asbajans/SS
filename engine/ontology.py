"""Ontology stage: seed docs → entity/relation types via LLM (task=ingest_ontology)."""

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
