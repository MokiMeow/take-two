"""Deterministic feasibility checks; only a pass may reach approval."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from coordinator.constraints import Constraints, Manifest, Windows


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: Literal["pass", "fail", "needs_verification"]
    reasons: list[str]


def canonical_manifest_json(manifest: Manifest) -> str:
    """Stable JSON of approved data, excluding the manifest's own hash field."""
    return json.dumps(manifest.model_dump(mode="json", exclude={"manifest_hash"}),
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def manifest_hash(manifest: Manifest) -> str:
    return "sha256:" + hashlib.sha256(canonical_manifest_json(manifest).encode("utf-8")).hexdigest()


def check_manifest(manifest: Manifest, constraints: Constraints) -> CheckResult:
    """Check one scene against trusted constraints and occupied commitments.

    Availability is known only on days represented by supplied intervals. An
    absent future day is unresolved; an explicit empty list means unavailable.
    Light is required through photography, while setup/wrap consume people and
    location permission. Failures take precedence over unresolved facts.
    """
    failures: list[str] = []
    unknowns: list[str] = []
    begin = manifest.start - timedelta(minutes=manifest.setup_min)
    finish = manifest.end + timedelta(minutes=manifest.wrap_min)
    zone = ZoneInfo(constraints.timezone)

    for field in ("script_rev", "constraints_rev"):
        if getattr(manifest, field) != getattr(constraints, field):
            failures.append(f"The {field} revision is outdated or does not match current inputs.")

    def status_check(status: str, subject: str) -> None:
        if status == "refused":
            failures.append(f"{subject} is refused or not satisfied.")
        elif status != "confirmed":
            unknowns.append(f"{subject} needs verification.")

    def window_check(windows: Windows, subject: str) -> None:
        if windows == "unknown":
            unknowns.append(f"{subject} needs verification.")
            return
        if any(window.start <= begin and finish <= window.end for window in windows):
            return
        first_day, last_day = begin.astimezone(zone).date(), finish.astimezone(zone).date()
        day_is_known = not windows or any(
            window.start.astimezone(zone).date() <= last_day
            and window.end.astimezone(zone).date() >= first_day for window in windows
        )
        if day_is_known:
            failures.append(f"{subject} does not cover setup, shooting and wrap.")
        else:
            unknowns.append(f"{subject} on this day needs verification.")

    people = {person.id: person for person in constraints.people}
    for person_id in manifest.people:
        person = people.get(person_id)
        if person is None:
            unknowns.append(f"Person {person_id} is unknown; availability needs verification.")
            continue
        window_check(person.available, f"Person {person_id}'s availability")
        if person.hard_stop is not None and finish > person.hard_stop:
            failures.append(f"Person {person_id}'s hard stop is before the end of wrap.")

    location = next((item for item in constraints.locations if item.id == manifest.location), None)
    if location is None:
        unknowns.append(f"Location {manifest.location} needs verification.")
    else:
        status_check(location.permission, f"Location {location.id} permission")
        if not location.permission_authority:
            unknowns.append(f"Location {location.id} permission authority needs verification.")
        elif (location.permission_confirmed_by is not None
              and location.permission_confirmed_by != location.permission_authority):
            failures.append(f"Location {location.id} permission was not confirmed by its named authority.")
        window_check(location.windows, f"Location {location.id}'s permission window")
        if manifest.requires_light:
            if location.light_until is None:
                unknowns.append(f"Location {location.id}'s light deadline needs verification.")
            elif manifest.end > location.light_until:
                failures.append(f"Location {location.id}'s light ends before shooting finishes.")

    for capability in manifest.capabilities:
        status_check(constraints.capabilities.get(capability, "unknown"), f"Capability {capability}")

    scene = next((item for item in constraints.scenes if item.id == manifest.scene_id), None)
    if scene is None:
        unknowns.append(f"Scene {manifest.scene_id}'s hard story rules need verification.")
    else:
        for person in sorted(set(scene.required_people)-set(manifest.people)):
            failures.append(f'Required cast/crew {person} is missing from the manifest.')
        for capability in sorted(set(scene.required_capabilities)-set(manifest.capabilities)):
            failures.append(f'Required capability {capability} is missing from the manifest.')
        verified = scene.verified_facts.get(manifest.location, {})
        for rule in scene.hard:
            status_check(verified.get(rule, "unknown"), f"Hard story rule '{rule}'")

    for person_id in manifest.people:
        occupied = [item for item in constraints.commitments if item.person_id == person_id]
        if any(item.start < finish and begin < item.end for item in occupied):
            failures.append(f"Person {person_id} has an overlapping commitment.")
        before = [item for item in occupied if item.end <= begin]
        after = [item for item in occupied if item.start >= finish]
        adjacent = []
        if before:
            adjacent.append(max(before, key=lambda item: item.end))
        if after:
            adjacent.append(min(after, key=lambda item: item.start))
        for prior in adjacent:
            if prior.end <= begin:
                origin, destination, gap = prior.location, manifest.location, begin - prior.end
            else:
                origin, destination, gap = manifest.location, prior.location, prior.start - finish
            if origin == destination:
                continue
            route = f"{origin}->{destination}"
            minutes = constraints.travel_min.get(route)
            if minutes is None:
                unknowns.append(f"Travel {route} for {person_id} needs verification.")
            elif gap < timedelta(minutes=minutes):
                failures.append(f"Person {person_id} has insufficient travel time for {route} ({minutes} minutes).")

    result: Literal["pass", "fail", "needs_verification"] = (
        "fail" if failures else "needs_verification" if unknowns else "pass"
    )
    reasons = failures + unknowns
    return CheckResult(result=result, reasons=reasons[:99]+(['Further check reasons omitted.'] if len(reasons)>99 else []))
