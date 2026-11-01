"""Hard contract checks for Exodia Tower's approved companion-art brief.

This test validates the production specification, NOT nonexistent art assets.
"""
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ART = REPO / "docs" / "companion_art_contract.json"


def test_fleet_and_exact_owner_requested_art_coverage():
    art = json.loads(ART.read_text(encoding="utf-8"))
    assert art["schema_version"] == "exodia.companion-art/v1"
    assert [person["id"] for person in art["fleet"]] == [
        "kiko", "router", "memory", "archives", "inventory",
        "vault", "ninja", "cache", "strategy", "nova"
    ]
    assert len(art["emotions"]) == 20
    assert len(art["actions"]) == 13
    assert len(art["turnaround"]) == 5
    assert len(art["details"]) == 4
    for category in ("emotions", "actions", "turnaround", "details"):
        items = art[category]
        assert len({item["id"] for item in items}) == len(items)


def test_benchmark_fingerprint_and_production_status_are_honest():
    art = json.loads(ART.read_text(encoding="utf-8"))
    reference = art["benchmark"]
    assert len(reference["sha256"]) == 64
    assert reference["status"] == "owner_approved_reference_pending_repo_import"
    assert "silver-lavender" in art["visual_style"]["albedo_hair"]
    assert all(value == "not_started" for key, value in art["production"].items()
               if key != "reference_scene")
    assert "static whole-body wobble" in art["forbidden_shortcuts"]
    assert (REPO / "SKILL.md").exists()
    assert (REPO / "skills" / "exodia-companion-art" / "SKILL.md").exists()
