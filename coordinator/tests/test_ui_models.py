import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from coordinator.ui_models import ChangeCommand, State

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ui-state"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda path: path.name)
def test_every_snapshot_obeys_strict_contract(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    state = State.model_validate(payload)
    assert state.model_dump(exclude_none=True) == payload
    assert len(path.read_text(encoding="utf-8").splitlines()) < 500


def test_story_demonstrates_revision_invalidation_and_explicit_current_ack() -> None:
    normal, hold, options, outdated, released, stale = [
        State.model_validate(load(name)) for name in (
            "01-normal.json", "02-hold.json", "03-two-options.json",
            "04-outdated.json", "05-released.json", "06-stale-reply.json",
        )
    ]
    assert normal.revisions.constraints == 1
    assert hold.scenes[2].validity == "held"
    assert all(scene.validity == "valid" for scene in hold.scenes[:2])
    assert options.decision is not None
    assert sum(c.check.result == "pass" for c in options.decision.candidates) == 2
    assert {c.manifest.location for c in options.decision.candidates if c.check.result == "fail"} == {"courtyard"}
    assert outdated.decision is not None
    assert outdated.decision.status == "closed_outdated"
    assert outdated.decision.bound.constraints == 2 < outdated.revisions.constraints
    assert released.decision is not None and released.decision.answer is not None
    assert released.decision.answer.candidate_id == "s3-stairwell-reduced"
    assert released.releases[1].status == "superseded"
    assert len(released.releases[0].acks.confirmed) == 2
    assert any(item.kind == "stale_reply" for item in stale.timeline)
    assert {a.person for a in stale.releases[0].acks.confirmed} == set(stale.releases[0].acks.expected)


@pytest.mark.parametrize("mutation", [
    lambda state: state.update(secret="unexpected"),
    lambda state: state["revisions"].update(constraints="1"),
    lambda state: state["production"].update(now="2026-11-06T14:00:00"),
    lambda state: state["production"].update(now="2026-11-06T14:00:00Z"),
    lambda state: state["scenes"][0].update(validity="maybe"),
    lambda state: state["releases"][0].update(call_sheet_url="/media/../../secret.png"),
])
def test_invalid_wire_data_is_rejected(mutation) -> None:
    payload = load("01-normal.json")
    mutation(payload)
    with pytest.raises(ValidationError):
        State.model_validate(payload)


def test_change_command_has_no_hidden_source_or_approval_fields() -> None:
    command = dict(entity="location", target="rooftop", field="permission", value="refused", reporter="producer")
    assert ChangeCommand.model_validate(command).reporter == "producer"
    with pytest.raises(ValidationError):
        ChangeCommand.model_validate({**command, "approved": True})


@pytest.mark.parametrize("field,item,limit", [
    ("scenes", lambda state: state["scenes"][0], 200),
    ("changes", lambda state: load("02-hold.json")["changes"][0], 200),
    ("jobs", lambda state: load("02-hold.json")["jobs"][0], 20),
    ("releases", lambda state: state["releases"][0], 200),
    ("crew", lambda state: state["crew"][0], 500),
    ("timeline", lambda state: state["timeline"][0], 200),
])
def test_snapshot_collections_have_finite_capacity(field, item, limit: int) -> None:
    payload = load("01-normal.json")
    payload[field] = [item(payload)] * (limit + 1)
    with pytest.raises(ValidationError):
        State.model_validate(payload)


def test_snapshot_strings_and_nested_candidates_are_bounded() -> None:
    payload = load("03-two-options.json")
    payload["decision"]["candidates"] *= 7
    with pytest.raises(ValidationError):
        State.model_validate(payload)
    payload = load("01-normal.json")
    payload["releases"][0]["summary"] = "x" * 4097
    with pytest.raises(ValidationError):
        State.model_validate(payload)
