"""Bounded fixed renderer invocation; placeholders are visibly text files."""
import asyncio
import hashlib
import json
import shutil
import re
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel


class RenderError(RuntimeError):
    pass


class RenderResult(BaseModel):
    path: Path
    placeholder: bool
    manifest_hash: str


class RenderBridge:
    def __init__(self, artifacts_dir: Path, *, cli: Path = Path('render/cli.mjs'), timeout: int = 120) -> None:
        self.artifacts_dir = artifacts_dir.resolve()
        self.cli = cli.resolve()
        self.timeout = min(max(timeout, 1), 300)

    async def render(self, kind: Literal['preview', 'callsheet'], manifest: dict, props: dict | None = None) -> RenderResult:
        if kind not in ('preview', 'callsheet'):
            raise RenderError('Unsupported render kind.')
        canonical = {key: value for key, value in manifest.items() if key != 'manifest_hash'}
        content = json.dumps(canonical, sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=False).encode()
        if len(content) > 262144:
            raise RenderError('Manifest exceeds 256 KiB.')
        digest = 'sha256:' + hashlib.sha256(content).hexdigest()
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        stem = f'{kind}-{uuid4()}'
        manifest_path = self.artifacts_dir / f'{stem}.json'
        presentation = json.dumps(props if props is not None else manifest, ensure_ascii=False, allow_nan=False).encode()
        if len(presentation) > 262144:
            raise RenderError('Render props exceed 256 KiB.')
        manifest_path.write_bytes(presentation)
        if not self.cli.is_file():
            path = self.artifacts_dir / f'{stem}.placeholder.txt'
            path.write_text('PLACEHOLDER: renderer is not installed; this is not a preview or call sheet.\n', encoding='utf-8', newline='\n')
            return RenderResult(path=path, placeholder=True, manifest_hash=digest)
        node = shutil.which('node')
        if not node:
            raise RenderError('Node executable was not found.')
        path = self.artifacts_dir / f'{stem}.{ "mp4" if kind == "preview" else "png"}'
        # Drain stderr continuously, keeping only its final 2 KiB.
        process = await asyncio.create_subprocess_exec(
            node, str(self.cli), '--kind', kind, '--manifest', str(manifest_path), '--out', str(path),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        async def diagnostic() -> str:
            tail = b''
            while chunk := await process.stderr.read(1024):
                tail = (tail+chunk)[-2048:]
            lines = [line.removeprefix('render-error:').strip() for line in tail.decode('utf-8',errors='replace').splitlines() if line.startswith('render-error:')]
            value = lines[-1] if lines else 'Renderer failed or produced an invalid-size artifact.'
            value = re.sub(r'(?i)(bearer\s+|(?:token|api[_-]?key|secret)[=: ]+)[^\s,;]+', r'\1[redacted]', value)
            return ''.join(c for c in value if c.isprintable())[:512]
        capture = asyncio.create_task(diagnostic())
        try:
            await asyncio.wait_for(process.wait(), timeout=self.timeout)
            reason = await capture
        except (TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.kill()  # Exactly the subprocess created above, never another process.
            await process.wait()
            await capture
            raise
        if process.returncode or not path.is_file() or not 0 < path.stat().st_size <= 32 * 1024 * 1024:
            raise RenderError(reason)
        return RenderResult(path=path, placeholder=False, manifest_hash=digest)
