"""Strict wire models for docs/UI-CONTRACT.md; UI state is ledger-owned."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer, model_validator
from typing import Any
from coordinator.unicode_text import require_unicode


def _ist(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(hours=5, minutes=30):
        raise ValueError("timestamps must include the +05:30 offset")
    return value


Timestamp = Annotated[str, Field(max_length=64), AfterValidator(_ist)]
NonEmpty = Annotated[str, Field(min_length=1, max_length=512)]
Positive = Annotated[int, Field(ge=1)]
Minutes = Annotated[int, Field(ge=0)]
MediaURL = Annotated[str, Field(pattern=r"^/media/[A-Za-z0-9_.-]+\.(mp4|png)$")]
Entity = Literal["location", "person", "scene", "capability"]
ChangeStatus = Literal["recorded", "pending_confirmation", "rejected"]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_max_length=4096)

    @model_validator(mode='before')
    @classmethod
    def valid_unicode(cls, value: Any) -> Any:
        return require_unicode(value)


class Production(WireModel):
    id: NonEmpty
    title: NonEmpty
    timezone: Literal["Asia/Kolkata"]
    now: Timestamp
    day: NonEmpty


class Revisions(WireModel):
    script: Positive
    constraints: Positive


class Plan(WireModel):
    location: NonEmpty
    start: Timestamp
    end: Timestamp
    setup_min: Minutes
    wrap_min: Minutes
    people: Annotated[list[NonEmpty], Field(max_length=500)]


class Scene(WireModel):
    id: NonEmpty
    number: Positive
    title: NonEmpty
    hard: Annotated[list[str], Field(max_length=40)]
    preferences: Annotated[list[str], Field(max_length=40)]
    validity: Literal["valid", "held", "invalid"]
    hold_reason: str | None = None
    plan: Plan | None = None


class ChangeCommand(WireModel):
    entity: Entity
    target: NonEmpty
    field: NonEmpty
    value: NonEmpty
    reporter: NonEmpty


class Change(ChangeCommand):
    id: NonEmpty
    at: Timestamp
    recorded_at: Timestamp | None = None
    reporter_name: NonEmpty | None = None
    status: ChangeStatus
    source: Literal["mattermost", "discord", "control_room"]
    constraints_rev: Positive | None = None
    resolution: Literal['recorded', 'dismissed'] | None = None


class ChangeResponse(WireModel):
    change_id: NonEmpty
    status: ChangeStatus
    reason: str | None = None


class Job(WireModel):
    job_id: NonEmpty
    role: Literal["script-supervisor", "first-ad"]
    status: Literal["queued", "running", "done", "failed", "cancelled"]
    started_at: Timestamp
    deadline: Timestamp
    summary: str | None = None


class Check(WireModel):
    result: Literal["pass", "fail", "needs_verification"]
    reasons: Annotated[list[str], Field(max_length=100)]


class CandidateManifest(Plan):
    scene_id: NonEmpty
    shots: Annotated[list[NonEmpty], Field(max_length=100)]
    capabilities: Annotated[list[NonEmpty], Field(max_length=100)]


class Candidate(WireModel):
    candidate_id: NonEmpty
    label: NonEmpty
    story_cost: str
    check: Check
    manifest: CandidateManifest
    manifest_hash: NonEmpty
    preview_url: MediaURL | None = None
    preview_status: Literal["none", "rendering", "ready", "failed"]
    schedule: Annotated[list[CandidateManifest], Field(max_length=20)] | None = None


class Answer(WireModel):
    candidate_id: NonEmpty
    note: str | None = None
    answered_by: NonEmpty
    answered_by_name: NonEmpty | None = None
    at: Timestamp


class Decision(WireModel):
    request_id: NonEmpty
    status: Literal["open", "answered", "expired", "closed_outdated", "rejected_unauthorized"]
    question: NonEmpty
    authority: NonEmpty
    authority_name: NonEmpty | None = None
    bound: Revisions
    opened_at: Timestamp
    expires_at: Timestamp
    candidates: Annotated[list[Candidate], Field(max_length=20)]
    answer: Answer | None = None
    must_keep: Annotated[list[str], Field(max_length=100)] | None = None
    requirements_note: str | None = None


class Publication(WireModel):
    room: NonEmpty
    room_name: NonEmpty | None = None
    platform: Literal["discord", "mattermost"]
    status: Literal["pending", "sent", "uncertain", "failed"]


class Confirmation(WireModel):
    person: NonEmpty
    at: Timestamp


class Acks(WireModel):
    expected: Annotated[list[NonEmpty], Field(max_length=500)]
    confirmed: Annotated[list[Confirmation], Field(max_length=500)]
    policy: Literal["affected_only", "everyone"]


class Release(WireModel):
    release_id: NonEmpty
    number: Positive
    status: Literal["approved", "published", "superseded"]
    created_at: Timestamp
    manifest_hash: NonEmpty
    summary: str
    call_sheet_url: MediaURL | None = None
    preview_url: MediaURL | None = None
    publications: Annotated[list[Publication], Field(max_length=20)]
    acks: Acks
    duty_changes: dict[NonEmpty, Annotated[list[NonEmpty], Field(max_length=500)]] | None = None


class CrewMember(WireModel):
    id: NonEmpty
    name: NonEmpty
    role: NonEmpty
    role_label: NonEmpty | None = None
    call_time: Timestamp | None = None
    acked_release: Positive | None = None
    affected: bool | None = None
    since_confirmed: Annotated[list[NonEmpty], Field(max_length=500)] | None = None


class TimelineItem(WireModel):
    at: Timestamp
    kind: Literal["change", "hold", "job", "check", "render", "decision", "release", "ack", "stale_reply", "error"]
    text: NonEmpty
    ref: str | None = None


class State(WireModel):
    production: Production
    revisions: Revisions
    scenes: Annotated[list[Scene], Field(max_length=200)]
    changes: Annotated[list[Change], Field(max_length=200)]
    jobs: Annotated[list[Job], Field(max_length=20)]
    decision: Decision | None
    releases: Annotated[list[Release], Field(max_length=200)]
    crew: Annotated[list[CrewMember], Field(max_length=500)]
    timeline: Annotated[list[TimelineItem], Field(max_length=200)]

    @model_serializer(mode="wrap")
    def keep_required_null_decision(self, handler: SerializerFunctionWrapHandler) -> dict:
        result = handler(self)
        # This is a required nullable key, unlike the optional wire fields.
        if self.decision is None:
            result["decision"] = None
        return result
