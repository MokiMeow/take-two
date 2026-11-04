"""Read the review server and verify replay, artifacts and release audiences."""
import asyncio
import json
from pathlib import Path

import httpx

from coordinator.ui_models import State
from coordinator.unicode_text import require_unicode
from scripts.demo_day import normalized

ROOT=Path(__file__).resolve().parents[1]


async def main() -> None:
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8787',timeout=15) as http:
        response=await http.get('/api/state')
        response.raise_for_status()
        state=response.json()
        State.model_validate(state)
        require_unicode(state)
        assert state['revisions']==dict(script=1,constraints=5)
        assert len(state['changes'])==4
        assert [r['number'] for r in state['releases']]==[5,4,3,2,1]
        assert all(s['validity']=='valid' for s in state['scenes'])
        expected={1:['maya','dev','leela'],2:[],3:['maya','dev','leela'],4:[],5:['maya']}
        for r in state['releases']:
            assert r['acks']['expected']==expected[r['number']]
            assert {a['person'] for a in r['acks']['confirmed']}==set(r['acks']['expected'])
        files=list((ROOT/'fixtures/ui-state/day').glob('*.json'))
        assert len(files)==23
        final=json.loads((ROOT/'fixtures/ui-state/day/23-r5-confirmed.json').read_text(encoding='utf-8'))
        assert normalized(final)==normalized(state)
        one=json.loads((ROOT/'data/w6-normalized-1.json').read_text(encoding='utf-8'))
        two=json.loads((ROOT/'data/w6-normalized-2.json').read_text(encoding='utf-8'))
        four=json.loads((ROOT/'data/w6-normalized-4.json').read_text(encoding='utf-8'))
        assert one==two==four
        result=dict(day_fixtures=len(files),light_fixtures=len(list((ROOT/'fixtures/ui-state/light').glob('*.json'))),
            release='r5',expected=['maya'],confirmed=['maya'],normalized_runs_match=True,http={})
        for url in ('/',state['releases'][0]['call_sheet_url'],state['releases'][0]['preview_url']):
            media=await http.get(url)
            media.raise_for_status()
            result['http'][url]=media.status_code
            if url.endswith('.png'):
                assert media.content.startswith(b'\x89PNG\r\n\x1a\n')
            if url.endswith('.mp4'):
                assert media.content[4:8]==b'ftyp'
        (ROOT/'work/W6-state.json').write_text(json.dumps(state,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
        (ROOT/'data/w6-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps(result,indent=2))


if __name__=='__main__':
    asyncio.run(main())
