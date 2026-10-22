"""Unsigned, session-only hash-linked events; consistency checks are not authentication."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

GENESIS = '0' * 64
METADATA = ('schema_version', 'case_id', 'title', 'investigator_reference', 'notes', 'status', 'created_at')


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def content_hash(value):
    return sha256(canonical_bytes(value)).hexdigest()


def append_event(case, event_type, payload):
    events = case['audit_events']
    event = {'event_id': str(uuid4()), 'sequence': len(events) + 1,
             'case_id': case['case_id'], 'event_type': event_type,
             'recorded_at': datetime.now(timezone.utc).isoformat(),
             'actor_reference': case['investigator_reference'],
             'actor_verified': False, 'payload': deepcopy(payload),
             'previous_sha256': events[-1]['sha256'] if events else GENESIS}
    event['sha256'] = content_hash(event)
    events.append(event)
    case['updated_at'] = event['recorded_at']


def verify_case(case):
    """Check event links AND the current metadata/evidence/report projections.

    A party able to rewrite the entire case can recompute every hash. There is no
    signing key, independent timestamp, persistent ledger, or external trust root.
    """
    previous = GENESIS
    metadata = None
    evidence = []
    reports = []
    events = case.get('audit_events', [])
    if not events:
        return False
    try:
        for index, event in enumerate(events, 1):
            body = {key: value for key, value in event.items() if key != 'sha256'}
            if (event['sequence'] != index or event['previous_sha256'] != previous
                    or event['case_id'] != case['case_id'] or content_hash(body) != event['sha256']):
                return False
            previous = event['sha256']
            kind, payload = event['event_type'], event['payload']
            if index == 1 and kind != 'case_created':
                return False
            if kind == 'case_created':
                if index != 1:
                    return False
                metadata = payload['metadata']
            elif kind == 'case_updated':
                metadata = payload['metadata']
            elif kind == 'evidence_added':
                evidence.append(payload['evidence'])
            elif kind == 'report_attached':
                reports.append(payload['report_sha256'])
            elif kind != 'evidence_verified':
                return False
        return (metadata == {key: case[key] for key in METADATA}
                and evidence == case['evidence']
                and reports == [content_hash(report) for report in case['reports']]
                and case['updated_at'] == events[-1]['recorded_at'])
    except (KeyError, TypeError, ValueError):
        return False
