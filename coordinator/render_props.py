"""Pure presentation from canonical manifests and trusted script/crew metadata."""
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from coordinator.render_schema import CallSheetProps, PreviewProps


def preview_props(candidate: dict[str, Any], letter: str, scene: dict[str, Any],
                  crew: list[dict[str, Any]]) -> dict[str, Any]:
    m = candidate['manifest']
    names = {p['id']: p['name'] for p in crew}
    cast = {p['id'] for p in crew if p.get('role')=='actor'}
    if set(m['people'])-set(names):
        raise ValueError('Preview contains an unknown person')
    return PreviewProps.model_validate(dict(letter=letter, label=candidate['label'],
        scene_number=scene['number'], scene_title=scene['title'], location=m['location'],
        start=m['start'], end=m['end'], shots=m['shots'],
        people=[dict(id=p, name=names[p]) for p in m['people'] if p in cast], sunset=None, crowd=None,
        manifest_hash=candidate['manifest_hash'])).model_dump()


def operational(m: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in m.items() if k not in ('script_rev','constraints_rev','manifest_hash')}


def call_times(manifest: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for scene in manifest['scenes']:
        if scene.get('validity') in ('held','invalid'):
            continue
        time = (datetime.fromisoformat(scene['start'])-timedelta(minutes=scene['setup_min'])).astimezone(ZoneInfo('Asia/Kolkata')).isoformat()
        for person in scene['people']:
            if person not in result or datetime.fromisoformat(time)<datetime.fromisoformat(result[person]):
                result[person] = time
    return result


def callsheet_props(envelope: dict[str, Any]) -> dict[str, Any]:
    metadata = envelope['metadata']
    previous = envelope.get('previous_manifest') or dict(scenes=[])
    old = {s['scene_id']: s for s in previous['scenes']}
    actors = {p['id']:str(i+1) for i,p in enumerate(p for p in metadata['crew'] if p['role']=='actor')}
    titles = {s['id']: s for s in metadata['scenes']}
    scenes, locations = [], []
    for m in envelope['manifest']['scenes']:
        info = titles[m['scene_id']]
        row = dict(number=info['number'], title=info['title'],
            changed=operational(m)!=operational(old.get(m['scene_id'],{})))
        if m.get('validity') in ('held','invalid'):
            row.update(status='held',hold_reason=m['hold_reason'][:200])
        else:
            row.update(status='scheduled',location=m['location'],start=m['start'],end=m['end'],
                cast=[actors[p] for p in m['people'] if p in actors])
            if m['location'] not in locations:
                locations.append(m['location'])
        scenes.append(row)
    times, old_times = call_times(envelope['manifest']), call_times(previous)
    crew = [dict(name=p['name'],role=f"Actor ({actors[p['id']]})" if p['id'] in actors else p['role'].replace('_',' / ').title(),
        call_time=times.get(p['id']),changed=times.get(p['id'])!=old_times.get(p['id'])) for p in metadata['crew']]
    return CallSheetProps.model_validate(dict(production=metadata['production'],release=envelope['release'],
        general_call=min(times.values(),key=datetime.fromisoformat) if times else envelope['release']['created_at'],
        sunset=metadata.get('sunset'),scenes=scenes,crew=crew,
        locations=[dict(name=p.title(),note=None) for p in locations],
        confirm_hint=f"Reply \"confirm {envelope['release']['release_id']}\" in the crew room.")).model_dump()


def hhmm(value: str, zone: str = 'Asia/Kolkata') -> str:
    return datetime.fromisoformat(value).astimezone(ZoneInfo(zone)).strftime('%H:%M')


def release_text(envelope: dict[str, Any]) -> str:
    props = callsheet_props(envelope)
    r, prod = props['release'], props['production']
    colours = ['White','Blue','Pink','Yellow','Green','Goldenrod','Buff','Salmon','Cherry']
    colour = colours[(r['number']-1)%len(colours)].lower()
    lines = [f"TAKE TWO · Release {r['number']} ({colour} pages) · {prod['title']}, {prod['day']}",
        'What changed: '+r['summary']]
    old = {m['scene_id']:m for m in (envelope.get('previous_manifest') or {'scenes':[]})['scenes']}
    old_times = call_times(envelope.get('previous_manifest') or {'scenes':[]})
    for m in envelope['manifest']['scenes']:
        prior = old.get(m['scene_id'])
        if prior and 'start' in prior and 'start' in m and (m['start'],m['end'])!=(prior['start'],prior['end']):
            number = next(s['number'] for s in envelope['metadata']['scenes'] if s['id']==m['scene_id'])
            lines.append(f"Scene {number} moved: {hhmm(prior['start'])}–{hhmm(prior['end'])} → {hhmm(m['start'])}–{hhmm(m['end'])}.")
    for s in props['scenes']:
        mark = '*' if s['changed'] else ''
        if s['status']=='held':
            lines.append(f"Sc {s['number']}{mark} · {s['title']} · ON HOLD: {s['hold_reason']}")
        else:
            location = ('INT. ' if s['location']=='stairwell' else 'EXT. ')+s['location'].upper()
            lines.append(f"Sc {s['number']}{mark} · {s['title']} · {location} · {hhmm(s['start'])}–{hhmm(s['end'])}")
    lines.append('Call times: '+' · '.join(f"{p['name']} {hhmm(p['call_time']) if p['call_time'] else 'held'}" for p in props['crew'])+'   (* = changed)')
    changed_calls=[]
    for p,member in zip(props['crew'],envelope['metadata']['crew'],strict=True):
        if p['changed']:
            prior=old_times.get(member['id'])
            changed_calls.append(f"{p['name']} {hhmm(prior) if prior else 'none'} → {hhmm(p['call_time']) if p['call_time'] else 'held'}")
    lines.append('Re-confirm changed calls: '+('; '.join(changed_calls) or 'none; existing confirmations carry forward')+'.')
    for scene in envelope['manifest']['scenes']:
        if 'shots' in scene:
            number = next(s['number'] for s in envelope['metadata']['scenes'] if s['id']==scene['scene_id'])
            lines.append(f"Sc {number} coverage: {', '.join(scene['shots'])}; kit: {', '.join(scene['capabilities']) or 'none'}; setup {scene['setup_min']}m; wrap {scene['wrap_min']}m.")
    confirmation=f'Reply "confirm {r["release_id"]}".'
    if r['number']>1:
        confirmation+=f' Replies about release {r["number"]-1} will be corrected.'
    lines.append(confirmation)
    return '\n'.join(lines)
