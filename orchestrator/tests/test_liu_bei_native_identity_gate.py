"""A0 Liu Bei identity review never confuses technical PNG checks with approval."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from PIL import Image

from tools.liu_bei_native_identity_gate import (
    ROOT, LOCKED, PILOT_MANIFEST, audit_identity, main, sha256, verify_reference
)
import json


def manifest():
    return json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))


def test_reference_is_real_composite_and_still_unapproved():
    result = audit_identity(manifest(), ROOT)
    assert result["reference"]["sha256"] == "65562dfd75c83ac46cf6ec2dec05bff9d59812bd22287750bd48833f94bc584e"
    assert result["reference"]["dimensions"] == [1122, 1402]
    assert result["technical_source_pass"] is False
    assert result["owner_identity_approval"] == "pending"
    assert result["production_release_enabled"] is False


def test_rejects_authority_changes():
    m = manifest()
    m["identity_reference"]["native_identity_owner_approved"] = True
    try:
        audit_identity(m, ROOT)
    except ValueError as e:
        assert str(e) == "unauthorized_identity_approval"
    else:
        raise AssertionError("Approval change was accepted")
    m = manifest(); m["production_release_enabled"] = True
    try: audit_identity(m, ROOT)
    except ValueError as e: assert "production_lock" in str(e)
    else: raise AssertionError("Release flip was accepted")


def test_non_native_and_poster_alias_rejected(tmp_path):
    m=manifest(); source=ROOT / m["identity_reference"]["path"]
    file=tmp_path / "poster.png"
    file.write_bytes(source.read_bytes())
    m["identity_reference"]["path"] = "poster.png"
    result=audit_identity(m,tmp_path,Path("poster.png"),sha256(file))
    assert result["technical_source_pass"] is False
    assert "not_native_1536x1920_png" in result["errors"]
    assert "historical_poster_cannot_be_master" in result["errors"]


def test_missing_sha_and_path_traversal_fail_closed(tmp_path):
    m=manifest()
    # Root for reference remains real; candidate path must remain within that root.
    r=audit_identity(m,ROOT,Path("../outside.png"),"a"*64)
    assert "candidate_missing_or_unsafe" in r["errors"]
    r=audit_identity(m,ROOT,Path("foo.png"))
    assert "expected_sha_required" in r["errors"]


def test_native_test_pixels_are_not_owner_approval(tmp_path):
    m=manifest(); m["identity_reference"]["path"] = "ref.png"
    ref=ROOT / manifest()["identity_reference"]["path"]
    (tmp_path/"ref.png").write_bytes(ref.read_bytes())
    img=Image.new("RGB", LOCKED)
    # Synthetic multi-color test fixture only, NOT an art candidate.
    from PIL import ImageDraw
    draw=ImageDraw.Draw(img)
    for y in range(0, LOCKED[1], 96):
        for x in range(0, LOCKED[0], 96):
            draw.rectangle((x, y, x + 95, y + 95), fill=(x//6%256, y//3%256, (x+y)//9%256))
    candidate=tmp_path/"fixture.png"
    img.save(candidate)
    r=audit_identity(m,tmp_path,Path("fixture.png"),sha256(candidate))
    assert r["technical_source_pass"] is True
    assert r["source_authenticity_verified"] is False
    assert r["image_bound_landmark_review"] == "pending"
    assert r["owner_identity_approval"] == "pending"
    assert r["five_state_pilot"] == "blocked_until_identity_approval"


def test_blank_does_not_qualify(tmp_path):
    m=manifest();m["identity_reference"]["path"]="ref.png"
    (tmp_path/"ref.png").write_bytes((ROOT/manifest()["identity_reference"]["path"]).read_bytes())
    file=tmp_path/"solid.png";Image.new("RGB",LOCKED,"#000000").save(file)
    r=audit_identity(m,tmp_path,Path("solid.png"),sha256(file))
    assert "flat_or_placeholder_image" in r["errors"]


def test_cli_reports_pending_while_keep_release_locked(capsys):
    status=main([])
    doc=json.loads(capsys.readouterr().out)
    assert status == 0 and doc["owner_identity_approval"] == "pending"
    assert main(["--require-native-candidate"]) == 2
