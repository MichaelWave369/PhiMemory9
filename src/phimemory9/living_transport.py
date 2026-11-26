"""Authenticated in-process PhageLedger fixture endpoint; no network dispatch.

HMAC authenticates possession of separately registered symmetric fixture keys.
It is not a public signature, external identity attestation or action permit.
"""
from dataclasses import asdict
import hashlib
import hmac
import re

from .living_contract import canonical, commitment, fixture_id, Context
from .living_store import _new, _epoch, _json

PACKET_SCHEMA = 'phageledger-local-fixture/v1'
FIELDS = {'schema','synthetic','packet_id','source','destination','purpose','project','app',
          'tags','not_before','expires_at','policy_sha256','gene_ids','evidence_event',
          'payload_sha256','authority'}


def _mac(key, value):
    return hmac.new(key,b'phageledger-local-fixture/v1\0'+canonical(value),hashlib.sha256).hexdigest()


def pack(store, ids, source, destination, context, *, now, expires_at, expected_policy):
    store.authenticate(source)
    store.authenticate(destination)
    _epoch(now); _epoch(expires_at)
    if not 0 < expires_at-now <= 3600 or source.principal_id == destination.principal_id:
        raise ValueError('invalid packet lifetime or endpoint pair')
    if context.destination != destination.principal_id:
        raise PermissionError('explicit destination mismatch')
    with store.engine.transaction():
        event = store.evaluate(ids,source,context,'transfer',now=now,expected_policy=expected_policy)
        if not event.admitted_ids or event.held:
            raise PermissionError('all payload references require current transfer consent')
        payload = [dict(store._gene(gid)) for gid in event.admitted_ids]
        # Commit metadata identity/state only. No content is carried or executed.
        body = dict(schema=PACKET_SCHEMA,synthetic=True,packet_id=_new(),
            source=source.principal_id,destination=destination.principal_id,purpose=context.purpose,
            project=context.project,app=context.app,tags=sorted(context.tags),not_before=now,
            expires_at=expires_at,policy_sha256=expected_policy,gene_ids=list(event.admitted_ids),
            evidence_event=event.event_id,payload_sha256=commitment('living-memory.payload.v1',payload),
            authority='NONE')
        return dict(body=body,mac=_mac(source.key,body))


def admit(store, packet, source, destination, *, now):
    """Validate fresh policy and consent BEFORE idempotent receipt reuse."""
    store.authenticate(source)
    store.authenticate(destination)
    _epoch(now)
    canonical(packet)
    if type(packet) is not dict or set(packet) != {'body','mac'}:
        raise ValueError('invalid signed packet')
    body, mac = packet['body'], packet['mac']
    if type(body) is not dict or set(body) != FIELDS:
        raise ValueError('invalid packet fields')
    if type(mac) is not str or not re.fullmatch('[0-9a-f]{64}',mac):
        raise ValueError('invalid authentication code')
    if not hmac.compare_digest(mac,_mac(source.key,body)):
        raise PermissionError('packet authentication failed')
    if body['schema'] != PACKET_SCHEMA or body['synthetic'] is not True or body['authority'] != 'NONE':
        raise ValueError('unsupported software fixture contract')
    fixture_id(body['packet_id']); fixture_id(body['evidence_event'])
    _epoch(body['not_before']); _epoch(body['expires_at'])
    if (source.principal_id != body['source'] or destination.principal_id != body['destination'] or
            source.principal_id == destination.principal_id):
        raise PermissionError('authenticated endpoint mismatch')
    if not 0 < body['expires_at']-body['not_before'] <= 3600 or not body['not_before'] <= now < body['expires_at']:
        raise PermissionError('packet outside validity window')
    context = Context(body['project'],body['app'],body['purpose'],tuple(body['tags']),body['destination'])
    scope = store._context(context)
    ids = body['gene_ids']
    if type(ids) is not list or not 1 <= len(ids) <= 9 or ids != sorted(set(ids)):
        raise ValueError('invalid payload references')
    with store.engine.transaction():
        if any(store._reason(gid,source.principal_id,scope,'transfer',now,body['policy_sha256'])
               for gid in ids):
            raise PermissionError('current policy, scope or consent denied')
        payload = [dict(store._gene(gid)) for gid in ids]
        if body['payload_sha256'] != commitment('living-memory.payload.v1',payload):
            raise PermissionError('payload reference changed')
        event = store.db.execute('SELECT body_json FROM lm_events WHERE event_id=? AND kind=?',
                                 (body['evidence_event'],'expression')).fetchone()
        if event is None: raise PermissionError('receipt lineage missing')
        from .living_contract import strict_loads
        evidence = strict_loads(event[0])
        if (evidence['admitted_ids'] != ids or evidence['held'] or evidence['operation'] != 'transfer' or
            evidence['policy_sha256'] != body['policy_sha256'] or evidence['context'] != scope or
            evidence['principal'] != source.principal_id):
            raise PermissionError('receipt lineage substitution')
        replay_id = store.opaque(source.principal_id+'\0'+body['packet_id'])
        body_check = store.opaque(canonical(body).decode())
        prior = store.db.execute('SELECT body_check FROM lm_guard.replays WHERE opaque_id=?', (replay_id,)).fetchone()
        if prior:
            if not hmac.compare_digest(prior[0],body_check):
                raise PermissionError('reused packet ID with altered body')
            receipt = store.db.execute('SELECT body_json FROM lm_receipts WHERE replay_id=?', (replay_id,)).fetchone()
            if receipt is None: raise PermissionError('durable replay held after restoration or deletion')
            return strict_loads(receipt[0])
        receipt_body = dict(schema='phageledger-local-receipt/v1',packet_id=body['packet_id'],
            packet_sha256=commitment('phageledger.packet.v1',body),evidence_event=body['evidence_event'],
            policy_sha256=body['policy_sha256'],destination=destination.principal_id,
            status='ACCEPTED_FIXTURE_METADATA',authority='NONE',admitted_at=now)
        receipt = dict(body=receipt_body,mac=_mac(destination.key,receipt_body))
        store.db.execute('INSERT INTO lm_guard.replays VALUES (?,?)',(replay_id,body_check))
        store.db.execute('INSERT INTO lm_receipts VALUES (?,?)',(replay_id,_json(receipt)))
        return receipt


def verify_receipt(receipt, destination):
    if type(receipt) is not dict or set(receipt) != {'body','mac'}:
        raise ValueError('invalid receipt')
    return (type(receipt['mac']) is str and receipt['body'].get('destination') == destination.principal_id
            and hmac.compare_digest(receipt['mac'],_mac(destination.key,receipt['body'])))
