"""Template pack helpers (DB-backed templates, F4)."""
from engine.templates import (
    builtin_templates,
    get_template,
    template_from_pack,
    validate_pack,
)

VALID = {
    "language_default": "tr",
    "entity_types": ["Actor", "Issue"],
    "relation_types": ["supports", "opposes"],
    "persona_fields": ["age_group", "ideology"],
    "action_space": ["post", "comment", "silent"],
    "events_enabled": True,
    "report_outline": ["Özet", "Bulgular"],
    "sim_defaults": {"agents_n": 12, "rounds": 3, "platforms": 1},
}


def test_builtin_packs_valid():
    templates = builtin_templates()
    assert len(templates) >= 6
    for tpl in templates:
        pack = tpl.to_pack()
        assert validate_pack(pack) is None, tpl.key
        assert tpl.description
        rebuilt = template_from_pack(tpl.key, tpl.name, pack, tpl.description)
        assert rebuilt.action_space == tpl.action_space
        assert rebuilt.entity_types == tpl.entity_types
        assert rebuilt.sim_defaults == tpl.sim_defaults


def test_validate_pack_rejects_missing_fields():
    assert validate_pack({}) is not None
    assert validate_pack({"entity_types": ["A"]}) is not None


def test_validate_pack_rejects_bad_values():
    bad = dict(VALID, language_default="de")
    assert validate_pack(bad) is not None
    bad = dict(VALID, sim_defaults={"agents_n": 0, "rounds": 3, "platforms": 1})
    assert validate_pack(bad) is not None
    bad = dict(VALID, sim_defaults={"agents_n": 12, "rounds": 500, "platforms": 1})
    assert validate_pack(bad) is not None
    bad = dict(VALID, action_space=[])
    assert validate_pack(bad) is not None


def test_unknown_builtin_raises():
    try:
        get_template("nope")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")
