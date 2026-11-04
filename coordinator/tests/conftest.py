"""Each run owns a fresh temp root; old Windows owner-only ACLs are not reusable."""
from pathlib import Path
from uuid import uuid4

import pytest


def pytest_configure(config: pytest.Config) -> None:
    if config.option.basetemp is None:
        parent = Path(__file__).resolve().parents[2] / 'data' / 'test-runs'
        parent.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(parent / f'run-{uuid4().hex}')
