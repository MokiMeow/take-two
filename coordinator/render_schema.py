"""Pydantic mirror of render/src/schema.ts (strict renderer contract, W4).

Keep these bounds in sync with Zod; missing nullable fields are still errors.
"""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

def text(maximum: int) -> type:
    return Annotated[str, Field(min_length=1, max_length=maximum)]

ISO = Annotated[str, Field(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:\d{2}|Z)$')]
Hash = Annotated[str, Field(pattern=r'^sha256:[0-9a-f]{7,64}$')]
Number = Annotated[int, Field(ge=0, le=999)]

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Person(Strict):
    id: text(64)
    name: text(40)

class PreviewProps(Strict):
    letter: Annotated[str, Field(pattern=r'^[A-Z]$')]
    label: text(80)
    scene_number: Number
    scene_title: text(80)
    location: text(40)
    start: ISO
    end: ISO
    shots: Annotated[list[text(30)], Field(min_length=1, max_length=6)]
    people: Annotated[list[Person], Field(max_length=8)]
    sunset: bool | None
    crowd: bool | None
    manifest_hash: Hash

class Scheduled(Strict):
    status: Literal['scheduled']
    number: Number
    title: text(80)
    location: text(40)
    start: ISO
    end: ISO
    cast: Annotated[list[text(8)], Field(max_length=8)]
    changed: bool

class Held(Strict):
    status: Literal['held']
    number: Number
    title: text(80)
    hold_reason: text(200)
    changed: bool

class Production(Strict):
    title: text(80)
    day: text(40)
    date: text(60)
    timezone: text(40)

class Release(Strict):
    number: Annotated[int, Field(ge=1, le=999)]
    release_id: text(64)
    manifest_hash: Hash
    summary: text(400)
    changes: Annotated[list[text(160)], Field(max_length=6)]
    created_at: ISO

class CrewRow(Strict):
    name: text(40)
    role: text(60)
    call_time: ISO | None
    changed: bool

class LocationRow(Strict):
    name: text(40)
    note: Annotated[str, Field(max_length=160)] | None

class CallSheetProps(Strict):
    production: Production
    release: Release
    general_call: ISO
    sunset: ISO | None
    scenes: Annotated[list[Annotated[Scheduled | Held, Field(discriminator='status')]], Field(min_length=1, max_length=20)]
    crew: Annotated[list[CrewRow], Field(max_length=30)]
    locations: Annotated[list[LocationRow], Field(max_length=8)]
    confirm_hint: text(120)
