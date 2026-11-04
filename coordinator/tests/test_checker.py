"""Feasibility tests use verified fixture facts, never an agent's verdict."""

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from coordinator.checker import canonical_manifest_json, check_manifest, manifest_hash
from coordinator.constraints import Constraints, Manifest

HARD = "confession is intelligible and confidential in the story"


def at(time: str, day: str = "06") -> str:
    return f"2026-11-{day}T{time}:00+05:30"


@pytest.fixture
def facts() -> dict[str, Any]:
    return {
        "timezone": "Asia/Kolkata", "script_rev": 1, "constraints_rev": 2,
        "people": [{"id": "maya", "role": "actor", "available": [f"{at('15:00')}/{at('20:00')}"],
                    "hard_stop": at("20:00")}],
        "locations": [
            {"id": "rooftop", "permission": "refused", "permission_authority": "producer", "windows": []},
            {"id": "courtyard", "permission": "confirmed", "permission_authority": "producer",
             "windows": [f"{at('14:00')}/{at('17:00')}"]},
            {"id": "stairwell", "permission": "confirmed", "permission_authority": "producer",
             "windows": [f"{at('14:00')}/{at('20:00')}"]},
            {"id": "park", "permission": "confirmed", "permission_authority": "producer",
             "windows": [f"{at('14:00')}/{at('20:00')}"], "light_until": at("18:20")},
        ],
        "travel_min": {"rooftop->stairwell": 15, "stairwell->rooftop": 30},
        "capabilities": {"gimbal": "confirmed", "second_camera": "unknown", "crane": "refused"},
        "scenes": [{"id": "s3", "hard": [HARD], "preferences": ["sunset", "visually secluded"],
                    "verified_facts": {place: {HARD: "confirmed"} for place in ["stairwell", "park", "courtyard"]}}],
    }


@pytest.fixture
def plan() -> dict[str, Any]:
    return {"scene_id": "s3", "location": "stairwell", "start": at("16:00"), "end": at("17:15"),
            "setup_min": 15, "wrap_min": 10, "people": ["maya"], "shots": ["wide", "two-shot"],
            "capabilities": ["gimbal"], "script_rev": 1, "constraints_rev": 2}


def verdict(plan: dict[str, Any], facts: dict[str, Any], want: str, reason: str = "") -> None:
    result = check_manifest(Manifest.model_validate(plan), Constraints.model_validate(facts))
    assert result.result == want
    if reason:
        assert any(reason in item.lower() for item in result.reasons), result.reasons


@pytest.mark.parametrize(("place", "start", "end", "want"), [
    ("courtyard", "16:00", "17:15", "fail"),
    ("stairwell", "16:00", "17:15", "pass"),
    ("park", "16:45", "18:15", "pass"),
    ("stairwell", "16:30", "17:15", "pass"),
    ("rooftop", "16:00", "17:15", "fail"),
])
def test_flow_location_options(facts: dict[str, Any], plan: dict[str, Any], place: str,
                               start: str, end: str, want: str) -> None:
    plan.update(location=place, start=at(start), end=at(end), setup_min=0, wrap_min=0)
    plan["requires_light"] = place == "park"
    verdict(plan, facts, want)


def test_early_departure_invalidates_park(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["people"][0]["hard_stop"] = at("18:00")
    plan.update(location="park", start=at("16:45"), end=at("18:15"))
    verdict(plan, facts, "fail", "hard stop")


def test_day_two_is_unknown(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    plan.update(start=at("16:00", "07"), end=at("17:15", "07"))
    facts["people"][0]["hard_stop"] = None
    verdict(plan, facts, "needs_verification", "availability")


@pytest.mark.parametrize("field", ["script_rev", "constraints_rev"])
def test_old_revisions_cannot_pass(facts: dict[str, Any], plan: dict[str, Any], field: str) -> None:
    plan[field] = 99
    verdict(plan, facts, "fail", "revision")


@pytest.mark.parametrize(("status", "want"), [("unknown", "needs_verification"), ("refused", "fail")])
def test_permission_dependency(facts: dict[str, Any], plan: dict[str, Any], status: str, want: str) -> None:
    facts["locations"][2]["permission"] = status
    verdict(plan, facts, want, "permission")


def test_permission_needs_named_authority(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["locations"][2].pop("permission_authority")
    verdict(plan, facts, "needs_verification", "authority")


def test_director_cannot_grant_location_permission(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["locations"][2]["permission_confirmed_by"] = "director"
    verdict(plan, facts, "fail", "authority")


@pytest.mark.parametrize(("capability", "want"), [
    ("gimbal", "pass"), ("second_camera", "needs_verification"),
    ("crane", "fail"), ("teleprompter", "needs_verification"),
])
def test_required_capabilities(facts: dict[str, Any], plan: dict[str, Any], capability: str, want: str) -> None:
    plan["capabilities"] = [capability]
    verdict(plan, facts, want)


@pytest.mark.parametrize(("start", "end", "setup", "wrap", "want"), [
    ("15:00", "17:15", 0, 0, "pass"),
    ("15:00", "17:15", 1, 0, "fail"),
    ("19:00", "20:00", 0, 0, "pass"),
    ("19:00", "20:00", 0, 1, "fail"),
])
def test_setup_wrap_count_against_availability(facts: dict[str, Any], plan: dict[str, Any],
                                              start: str, end: str, setup: int, wrap: int, want: str) -> None:
    plan.update(start=at(start), end=at(end), setup_min=setup, wrap_min=wrap)
    verdict(plan, facts, want)


def test_setup_wrap_count_against_permission_window(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    plan.update(location="courtyard", end=at("17:00"))
    verdict(plan, facts, "fail", "window")


def test_wrap_counts_against_hard_stop(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["people"][0]["hard_stop"] = at("17:15")
    verdict(plan, facts, "fail", "hard stop")


@pytest.mark.parametrize(("light", "want"), [("17:15", "pass"), ("17:14", "fail"), (None, "needs_verification")])
def test_light_is_required_only_when_used(facts: dict[str, Any], plan: dict[str, Any], light: str | None, want: str) -> None:
    facts["locations"][2]["light_until"] = at(light) if light else None
    plan["requires_light"] = True
    verdict(plan, facts, want, "light" if want != "pass" else "")


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("people", ["unknown-person"], "person"), ("location", "unknown-place", "location"),
    ("scene_id", "unknown-scene", "scene"),
])
def test_missing_entities_never_pass(facts: dict[str, Any], plan: dict[str, Any], field: str,
                                   value: Any, reason: str) -> None:
    plan[field] = value
    verdict(plan, facts, "needs_verification", reason)


@pytest.mark.parametrize(("field", "index"), [("people", 0), ("locations", 2)])
def test_unknown_windows_never_pass(facts: dict[str, Any], plan: dict[str, Any], field: str, index: int) -> None:
    facts[field][index]["available" if field == "people" else "windows"] = "unknown"
    verdict(plan, facts, "needs_verification")


@pytest.mark.parametrize(("fact", "want"), [("confirmed", "pass"), ("refused", "fail"), ("unknown", "needs_verification")])
def test_hard_story_rules_use_verified_facts(facts: dict[str, Any], plan: dict[str, Any], fact: str, want: str) -> None:
    facts["scenes"][0]["verified_facts"]["stairwell"][HARD] = fact
    verdict(plan, facts, want)


def test_missing_story_evidence_is_not_agent_approval(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["scenes"][0]["verified_facts"] = {}
    verdict(plan, facts, "needs_verification", "story")


def test_director_new_hard_note_must_be_verified(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["scenes"][0]["hard"].append("keep the confession private")
    verdict(plan, facts, "needs_verification", "story")


@pytest.mark.parametrize(("travel", "want"), [(15, "pass"), (16, "fail"), (None, "needs_verification")])
def test_travel_uses_setup_start(facts: dict[str, Any], plan: dict[str, Any], travel: int | None, want: str) -> None:
    facts["commitments"] = [{"person_id": "maya", "location": "rooftop", "start": at("15:00"), "end": at("15:30")}]
    facts["travel_min"] = {} if travel is None else {"rooftop->stairwell": travel}
    verdict(plan, facts, want)


def test_reverse_travel_is_not_inferred(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["commitments"] = [{"person_id": "maya", "location": "rooftop", "start": at("17:45"), "end": at("18:00")}]
    verdict(plan, facts, "fail", "travel")


def test_same_location_needs_no_travel_fact(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["commitments"] = [{"person_id": "maya", "location": "stairwell", "start": at("15:00"), "end": at("15:45")}]
    facts["travel_min"] = {}
    verdict(plan, facts, "pass")


def test_overlapping_commitment_fails(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["commitments"] = [{"person_id": "maya", "location": "stairwell", "start": at("17:20"), "end": at("18:00")}]
    verdict(plan, facts, "fail", "overlap")


def test_failure_wins_over_unknown(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    plan.update(location="rooftop", capabilities=["second_camera"])
    result = check_manifest(Manifest.model_validate(plan), Constraints.model_validate(facts))
    assert result.result == "fail"
    assert any("permission" in reason.lower() for reason in result.reasons)
    assert any("second_camera" in reason for reason in result.reasons)


def test_utc_times_compare_as_instants(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    plan.update(start="2026-11-06T10:30:00Z", end="2026-11-06T11:45:00Z")
    verdict(plan, facts, "pass")


@pytest.mark.parametrize("patch", [
    {"start": "2026-11-06T16:00:00"}, {"end": at("15:00")}, {"setup_min": -1},
    {"wrap_min": -1}, {"setup_min": True}, {"shots": []}, {"people": ["maya", "maya"]},
])
def test_malformed_agent_manifests_are_rejected(plan: dict[str, Any], patch: dict[str, Any]) -> None:
    plan.update(patch)
    with pytest.raises(ValidationError):
        Manifest.model_validate(plan)


def test_invalid_timezone_rejected(facts: dict[str, Any]) -> None:
    facts["timezone"] = "Not/AZone"
    with pytest.raises(ValidationError):
        Constraints.model_validate(facts)


def test_manifest_hash_ignores_own_hash_and_mapping_order(plan: dict[str, Any]) -> None:
    original = Manifest.model_validate(plan)
    reordered = dict(reversed(list(plan.items())))
    reordered["manifest_hash"] = "sha256:" + "0" * 64
    assert manifest_hash(original) == manifest_hash(Manifest.model_validate(reordered))
    assert "manifest_hash" not in canonical_manifest_json(original)


def test_hash_changes_for_approved_content(plan: dict[str, Any]) -> None:
    other = deepcopy(plan)
    other["shots"] = ["wide"]
    assert manifest_hash(Manifest.model_validate(plan)) != manifest_hash(Manifest.model_validate(other))


def test_only_adjacent_commitments_require_direct_travel(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["commitments"] = [
        {"person_id": "maya", "location": "unknown-origin", "start": at("14:00"), "end": at("14:30")},
        {"person_id": "maya", "location": "stairwell", "start": at("15:00"), "end": at("15:30")},
        {"person_id": "maya", "location": "stairwell", "start": at("18:00"), "end": at("18:30")},
        {"person_id": "maya", "location": "unknown-destination", "start": at("19:00"), "end": at("19:30")},
    ]
    verdict(plan, facts, "pass")


@pytest.mark.parametrize("patch", [
    {"start": "0001-01-01T00:00:00+00:00", "end": "0001-01-01T01:00:00+00:00"},
    {"start": "9999-12-31T23:00:00+00:00", "end": "9999-12-31T23:59:00+00:00"},
])
def test_datetime_extremes_cannot_crash_checker(plan: dict[str, Any], patch: dict[str, Any]) -> None:
    plan.update(patch)
    with pytest.raises(ValidationError):
        Manifest.model_validate(plan)


def test_explicit_empty_availability_fails(facts: dict[str, Any], plan: dict[str, Any]) -> None:
    facts["people"][0]["available"] = []
    verdict(plan, facts, "fail", "availability")


@pytest.mark.parametrize("patch", [
    {"setup_min": 1441}, {"shots": [str(i) for i in range(101)]}, {"people": [" " ]},
])
def test_manifest_payload_limits(plan: dict[str, Any], patch: dict[str, Any]) -> None:
    plan.update(patch)
    with pytest.raises(ValidationError):
        Manifest.model_validate(plan)


def test_duplicate_constraint_ids_rejected(facts: dict[str, Any]) -> None:
    facts["people"].append(deepcopy(facts["people"][0]))
    with pytest.raises(ValidationError):
        Constraints.model_validate(facts)
