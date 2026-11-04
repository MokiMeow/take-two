"""Original wire models, checked against Switch commit 989225d8.

Protocol references: core/switch_core/bridges/agent/{api,protocol} and
console/packages/switch-agent-runtime/src/event-stream.ts in sandbox-quantum/switch.
Switch is copyright SandboxAQ, Apache-2.0 with modified Commons Clause.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic.alias_generators import to_camel


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntegrationProfile(WireModel):
    connection_model: Literal["always_on"] = "always_on"
    message_exchange: bool = True
    pre_invocation_mediation: list[str] = Field(default_factory=list)
    post_invocation_mediation: list[str] = Field(default_factory=list)
    event_reporting: list[str] = Field(default_factory=list)


class Registration(WireModel):
    name: str = "take-two-coordinator"
    description: str = "Take Two deterministic production coordinator"
    connector_type: str = "take-two-coordinator"
    integration_profile: IntegrationProfile = Field(default_factory=IntegrationProfile)
    overwrite: Literal[False] = False


class RegistrationResponse(BaseModel):
    id: str = Field(min_length=1)
    api_key: SecretStr


class OperationEnvelope(BaseModel):
    result: Any


class InternalDocument(BaseModel):
    id: str
    description: str = ""
    content: str


class Identity(WireModel):
    agent_id: str
    api_key: SecretStr
    connection_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=200)
    position: dict[str, int] = Field(default_factory=dict)
    cursor: int | None = None
    generation: int | None = None

    @field_validator("position", mode="before")
    @classmethod
    def valid_position(cls, value: dict[str, int]) -> dict[str, int]:
        if not isinstance(value, dict) or any(
               not isinstance(key, str) or
               (key != "s" and not (key.startswith("r:") and len(key) > 2))
               or type(seq) is not int or seq < 0 for key, seq in value.items()):
            raise ValueError("invalid Switch event position")
        return value


class SwitchFrame(WireModel):
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
    id: int | None = None


class DocumentResult(BaseModel):
    document_id: str
    status: str | None = None


class RoleHolder(BaseModel):
    name: str
    present_here: bool
    session_room: str | None = None


class RoomRole(BaseModel):
    name: str
    exclusive: bool = True
    held_by: list[RoleHolder] = Field(default_factory=list)


class TargetedMessage(BaseModel):
    event_id: str
    target_statuses: dict[str, str]


class MessageReceipt(BaseModel):
    event_id: str
    ok: bool = True


class RoomProvision(BaseModel):
    room_id: str
    room_name: str
    failed_attachments: list[Any] = Field(default_factory=list)
    attached_reference_ids: list[str] = Field(default_factory=list)
    created_reference_ids: list[str] = Field(default_factory=list)
    created_document_ids: list[str] = Field(default_factory=list)
    role_names: list[str] = Field(default_factory=list)


class QuestionOption(WireModel):
    id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1)
    description: str | None = None


class Question(WireModel):
    id: str = "choice"
    title: str
    prompt: str
    options: list[QuestionOption] = Field(min_length=1)
    multi_select: bool = False
    allow_custom_answer: bool = True


class QuestionPayload(WireModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=200)
    turn_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=200)
    kind: Literal["questions"] = "questions"
    title: str = Field(min_length=1)
    detail: str | None = None
    options: list[Any] = Field(default_factory=list, max_length=0)
    questions: list[Question] = Field(min_length=1)
    room_id: str = Field(min_length=1)
    thread_id: None = None
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("question expiry must include a timezone")
        return value


class ApprovalOutcome(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    session_id: str
    request_id: str
    kind: str
    state: str
    answer: str | None = None
    answers: list[dict[str, Any]] | None = None
    answered_by: str | None = None
    answered_at: datetime | None = None
    expires_at: datetime | None = None
    delivered_at: datetime | None = None
