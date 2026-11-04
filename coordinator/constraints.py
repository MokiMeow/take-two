"""Bounded, timezone-aware input models for the deterministic checker.

Verified facts belong to the human-maintained constraints, not worker proposals.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field,
                      StringConstraints, field_validator, model_validator)

FactStatus = Literal["confirmed", "refused", "unknown"]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Minutes = Annotated[int, Field(strict=True, ge=0, le=1440)]


def safe_datetime(value: datetime) -> datetime:
    # Leave room for setup/wrap arithmetic and conversion to any IANA timezone.
    if not 2 <= value.year <= 9998:
        raise ValueError("date is outside the supported scheduling range")
    return value


Timestamp = Annotated[AwareDatetime, AfterValidator(safe_datetime)]
VerifiedRules = Annotated[dict[Identifier, FactStatus], Field(max_length=100)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=2000, str_strip_whitespace=True, validate_assignment=True)


class TimeWindow(InputModel):
    start: Timestamp
    end: Timestamp

    @model_validator(mode="before")
    @classmethod
    def parse_interval(cls, value: Any) -> Any:
        if isinstance(value, str):
            parts = value.split("/")
            if len(parts) != 2:
                raise ValueError("window must contain start/end")
            return {"start": parts[0], "end": parts[1]}
        return value

    @model_validator(mode="after")
    def ordered(self) -> TimeWindow:
        if self.end <= self.start:
            raise ValueError("window end must be after start")
        return self


Windows = Annotated[list[TimeWindow], Field(max_length=100)] | Literal["unknown"]


class Person(InputModel):
    id: Identifier
    role: Identifier = "crew"
    available: Windows = "unknown"
    hard_stop: Timestamp | None = None


class Location(InputModel):
    id: Identifier
    exterior: bool = False
    permission: FactStatus = "unknown"
    permission_authority: Identifier | None = None
    permission_confirmed_by: Identifier | None = None
    windows: Windows = "unknown"
    light_until: Timestamp | None = None


class Scene(InputModel):
    id: Identifier
    hard: list[Identifier] = Field(default_factory=list, max_length=40)
    preferences: list[Identifier] = Field(default_factory=list, max_length=40)
    required_people: list[Identifier] = Field(default_factory=list, max_length=8)
    required_capabilities: list[Identifier] = Field(default_factory=list, max_length=30)
    capability_alternatives: dict[Identifier, list[list[Identifier]]] = Field(default_factory=dict, max_length=30)
    status: Literal['scheduled', 'held'] = 'scheduled'
    overrun: Minutes = 0
    overrun_start: Timestamp | None = None
    overrun_end: Timestamp | None = None
    verified_facts: dict[Identifier, VerifiedRules] = Field(default_factory=dict, max_length=100)

    @model_validator(mode='after')
    def bounded_alternatives_and_overrun(self) -> Scene:
        for alternatives in self.capability_alternatives.values():
            if not 1 <= len(alternatives) <= 5 or any(not 1 <= len(row) <= 5 for row in alternatives):
                raise ValueError('At most five nonempty kit alternatives of five capabilities')
        if self.overrun and (self.overrun_start is None or self.overrun_end is None or self.overrun_end <= self.overrun_start):
            raise ValueError('Overrun requires the original observed scene interval')
        return self


class Commitment(TimeWindow):
    """Previously recorded occupied time, including its own setup and wrap."""

    person_id: Identifier
    location: Identifier


class Constraints(InputModel):
    timezone: Identifier
    script_rev: int = Field(default=1, ge=1, strict=True)
    constraints_rev: int = Field(default=1, ge=1, strict=True)
    people: list[Person] = Field(default_factory=list, max_length=30)
    locations: list[Location] = Field(default_factory=list, max_length=8)
    travel_min: dict[Identifier, Minutes] = Field(default_factory=dict, max_length=1000)
    capabilities: dict[Identifier, FactStatus] = Field(default_factory=dict, max_length=200)
    scenes: list[Scene] = Field(default_factory=list, max_length=20)
    commitments: list[Commitment] = Field(default_factory=list, max_length=1000)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be a known IANA zone") from exc
        return value

    @model_validator(mode="after")
    def unique_ids(self) -> Constraints:
        for name in ("people", "locations", "scenes"):
            values = [item.id for item in getattr(self, name)]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {name} IDs")
        return self


class Manifest(InputModel):
    scene_id: Annotated[str, Field(min_length=1, max_length=64)]
    location: Annotated[str, Field(min_length=1, max_length=40)]
    start: Timestamp
    end: Timestamp
    setup_min: Minutes
    wrap_min: Minutes
    people: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(min_length=1, max_length=8)
    shots: list[Annotated[str, Field(min_length=1, max_length=30)]] = Field(min_length=1, max_length=6)
    capabilities: list[Identifier] = Field(default_factory=list, max_length=30)
    script_rev: int = Field(ge=1, strict=True)
    constraints_rev: int = Field(ge=1, strict=True)
    requires_light: bool = False
    manifest_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def valid_schedule(self) -> Manifest:
        if self.end <= self.start:
            raise ValueError("manifest end must be after start")
        for name in ("people", "shots", "capabilities"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {name}")
        return self
