"""Filesystem-only W6 review and public-artifact checks; never prints secrets."""
from pathlib import Path
import difflib
import json

from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/w6-baseline'


def main() -> None:
    paths=[]
    for folder in ('coordinator','scripts','fixtures','templates'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.yaml','.md','.json','.txt')
            and '__pycache__' not in p.parts and 'node_modules' not in p.parts and p.name!='latest-release.json')
    paths += [ROOT/'docs/UI-CONTRACT.md',ROOT/'pyproject.toml',ROOT/'uv.lock']
    diffs=[]
    authored=[]
    for path in sorted(paths):
        rel=path.relative_to(ROOT)
        before=BASE/rel
        old=before.read_bytes() if before.exists() else b''
        new=path.read_bytes()
        if old==new:
            continue
        text=new.decode('utf-8')
        assert b'\r' not in new, f'CRLF: {rel}'
        assert len(text.splitlines())<500, f'500-line bound: {rel}'
        authored.append(str(rel))
        diffs.extend(difflib.unified_diff(old.decode('utf-8').splitlines(True),text.splitlines(True),fromfile='before/'+rel.as_posix(),tofile=rel.as_posix()))
    for path in (ROOT/'fixtures/ui-state').glob('0?-*.json'):
        assert path.read_bytes()==(BASE/path.relative_to(ROOT)).read_bytes(), 'Legacy snapshot changed'
    secrets=[]
    for path in (ROOT/'.env',ROOT/'scripts/switch/.env',ROOT/'data/w4-demo/.env'):
        if path.exists():
            secrets.extend(v for k,v in dotenv_values(path).items() if v and len(v)>=12 and any(word in k.upper() for word in ('PASSWORD','TOKEN','KEY')))
    for folder in (ROOT/'data/w4-demo',ROOT/'data/w6-demo'):
        for path in folder.glob('*.json'):
            if path.stat().st_size>262144:
                continue
            data=json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data,dict) and isinstance(data.get('api_key'),str):
                secrets.append(data['api_key'])
    public=[*(ROOT/p for p in authored),*(p for p in ROOT.glob('work/W6-*') if p.suffix in ('.md','.py','.json'))]
    for path in public:
        text=path.read_text(encoding='utf-8')
        assert not any(secret in text for secret in secrets), f'Credential found in {path.relative_to(ROOT)}'
        assert '\r' not in text and len(text.splitlines())<500, f'Artifact bounds: {path.relative_to(ROOT)}'
    (ROOT/'data/w6-diff.txt').write_text(''.join(diffs),encoding='utf-8',newline='\n')
    result=dict(changed_files=authored,concurrent_changes=['scripts/prepare_renderer.py: renderer staging copy, not authored by W6'],
        legacy_fixtures_unchanged=True,lf=True,under_500_lines=True,known_secret_scan='clean')
    (ROOT/'data/w6-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
