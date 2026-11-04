"""The replay comparison retains reports even before they acquire revisions."""
from scripts.demo_day import normalized


def test_normalized_pending_report_has_no_constraint_revision() -> None:
    state = dict(revisions={}, scenes=[], changes=[dict(entity='scene', target='unconfirmed',
        field='report', value='I have to leave at 6', status='pending_confirmation')],
        jobs=[], decision=None, releases=[], crew=[])
    assert normalized(state)['changes'][0]['constraints_rev'] is None
