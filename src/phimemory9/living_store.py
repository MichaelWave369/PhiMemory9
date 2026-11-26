"""Versioned overlay on MemoryEngine, exclusively for newly created fixtures.

The separate attached guard is operator-controlled state. SQLite rollback
journals make mutations of both local files atomic. Restoring the memory file
alone cannot restore withdrawn consent, forgotten content or admitted packets.
Rolling back both files, stealing keys or bypassing this API is outside trust.
"""
from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import uuid

from .core import MemoryEngine, _digest
from .genomememory_preview import preview, _label, _labels
from .genomememory_chromosomes import chromosome_preview
from .living_contract import (SCHEMA, canonical, commitment, fixture_id, LocalIdentity,
    MemoryToken, MemoryGene, MemoryChromosome, Context, ConsentRecord, ExpressionEvent,
    RepairEvent)

OPERATIONS = {'express', 'transfer', 'learn'}
CURRENT_VERSION = 2


def _new():
    return 'fixture:'+uuid.uuid4().hex


def _epoch(now):
    if type(now) is not int or not 0 <= now <= 2**53-1:
        raise ValueError('integer fixture clock required')
    return now


def _json(value):
    return canonical(value).decode('ascii')


def _exclusive(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)


class LivingStore:
    """A trusted local operator API, not an HTTP service or production key vault."""

    @classmethod
    def create(cls, path, guard_path, operator, *, version=CURRENT_VERSION):
        if type(operator) is not LocalIdentity or type(version) is not int or version not in (1, 2):
            raise ValueError('fixture operator or schema version invalid')
        path, guard_path = Path(path), Path(guard_path)
        if path.resolve() == guard_path.resolve():
            raise ValueError('separate guard file required')
        # Never open or migrate an existing personal database.
        if path.exists() or guard_path.exists() or path.is_symlink() or guard_path.is_symlink():
            raise FileExistsError('new disposable fixture paths required')
        _exclusive(path)
        _exclusive(guard_path)
        self = cls.__new__(cls)
        self.engine = MemoryEngine(path)
        self.db = self.engine.db
        self.operator = operator
        self.path, self.guard_path = path, guard_path
        self.db.execute('ATTACH DATABASE ? AS lm_guard', (str(guard_path),))
        self.db.executescript('''
            CREATE TABLE lm_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE lm_tokens (token_id TEXT PRIMARY KEY, source_json TEXT NOT NULL);
            CREATE TABLE lm_genes (
                gene_id TEXT PRIMARY KEY, memory_id TEXT UNIQUE NOT NULL REFERENCES memories(id),
                token_id TEXT REFERENCES lm_tokens(token_id), metadata_json TEXT NOT NULL,
                revision INTEGER NOT NULL, state TEXT NOT NULL);
            CREATE TABLE lm_lineage (
                child_id TEXT REFERENCES lm_genes(gene_id), parent_id TEXT REFERENCES lm_genes(gene_id),
                PRIMARY KEY(child_id,parent_id));
            CREATE TABLE lm_chromosomes (
                chromosome_id TEXT PRIMARY KEY, project TEXT NOT NULL,
                parent_id TEXT REFERENCES lm_chromosomes(chromosome_id));
            CREATE TABLE lm_memberships (
                chromosome_id TEXT REFERENCES lm_chromosomes(chromosome_id),
                gene_id TEXT REFERENCES lm_genes(gene_id), PRIMARY KEY(chromosome_id,gene_id));
            CREATE TABLE lm_events (event_id TEXT PRIMARY KEY, kind TEXT NOT NULL, body_json TEXT NOT NULL);
            CREATE TABLE lm_consents (
                consent_id TEXT PRIMARY KEY, gene_id TEXT REFERENCES lm_genes(gene_id),
                principal_id TEXT NOT NULL, context_json TEXT NOT NULL, operation TEXT NOT NULL,
                policy_sha256 TEXT NOT NULL, gene_revision INTEGER NOT NULL,
                not_before INTEGER NOT NULL, expires_at INTEGER NOT NULL, withdrawn INTEGER NOT NULL);
            CREATE TABLE lm_copies (
                copy_id TEXT PRIMARY KEY, gene_id TEXT REFERENCES lm_genes(gene_id),
                kind TEXT NOT NULL, content TEXT NOT NULL);
            CREATE TABLE lm_receipts (replay_id TEXT PRIMARY KEY, body_json TEXT NOT NULL);
            CREATE TABLE lm_guard.meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE lm_guard.identities (principal_id TEXT PRIMARY KEY, key_check TEXT NOT NULL);
            CREATE TABLE lm_guard.revoked_identities (principal_id TEXT PRIMARY KEY);
            CREATE TABLE lm_guard.blocks (opaque_id TEXT PRIMARY KEY, action TEXT NOT NULL);
            CREATE TABLE lm_guard.withdrawals (consent_id TEXT PRIMARY KEY);
            CREATE TABLE lm_guard.replays (opaque_id TEXT PRIMARY KEY, body_check TEXT NOT NULL);
        ''')
        store_id = _new()
        with self.engine.transaction():
            blob = self.engine.create_blob('Living Memory disposable synthetic fixture')
            for k, v in {'schema':SCHEMA, 'version':'1', 'store_id':store_id,
                         'blob':blob, 'owner':operator.principal_id}.items():
                self.db.execute('INSERT INTO lm_meta VALUES (?,?)', (k,v))
            for k, v in {'schema':SCHEMA, 'store_id':store_id, 'policy_revision':'0',
                         'policy_json':'null'}.items():
                self.db.execute('INSERT INTO lm_guard.meta VALUES (?,?)', (k,v))
            self.register_identity(operator)
        if version == 2:
            self.upgrade_fixture()
        return self

    @classmethod
    def open(cls, path, guard_path, operator):
        path, guard_path = Path(path), Path(guard_path)
        if type(operator) is not LocalIdentity or path.resolve() == guard_path.resolve():
            raise ValueError('fixture operator or guard invalid')
        metadata = []
        for file, table in ((path, 'lm_meta'), (guard_path, 'meta')):
            if not file.is_file() or file.is_symlink():
                raise ValueError('existing regular fixture and guard files required')
            db = sqlite3.connect(file.resolve().as_uri()+'?mode=ro', uri=True)
            try:
                metadata.append(dict(db.execute('SELECT key,value FROM '+table)))
            finally:
                db.close()
        main, guard = metadata
        if (main.get('schema') != SCHEMA or guard.get('schema') != SCHEMA or
                main.get('version') not in ('1','2') or main.get('store_id') != guard.get('store_id') or
                main.get('owner') != operator.principal_id):
            raise ValueError('unknown fixture schema, owner or guard binding')
        self = cls.__new__(cls)
        self.engine = MemoryEngine(path)
        self.db = self.engine.db
        self.path, self.guard_path, self.operator = path, guard_path, operator
        try:
            self.db.execute('ATTACH DATABASE ? AS lm_guard', (str(guard_path),))
            self.authenticate(operator)
            self.reconcile_guard()
        except BaseException:
            self.engine.close()
            raise
        return self

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def close(self): self.engine.close()

    def _meta(self, key):
        return self.db.execute('SELECT value FROM lm_meta WHERE key=?', (key,)).fetchone()[0]

    def _guard(self, key):
        return self.db.execute('SELECT value FROM lm_guard.meta WHERE key=?', (key,)).fetchone()[0]

    def _key_check(self, identity):
        return hmac.new(identity.key, (self._meta('store_id')+'\0'+identity.principal_id).encode(),
                        hashlib.sha256).hexdigest()

    def register_identity(self, identity):
        if type(identity) is not LocalIdentity:
            raise ValueError('local identity required')
        # Only the authenticated fixture operator has access to this object.
        with self.engine.transaction():
            if self.db.execute('SELECT 1 FROM lm_guard.revoked_identities WHERE principal_id=?',
                               (identity.principal_id,)).fetchone():
                raise PermissionError('revoked identity cannot reactivate')
            old = self.db.execute('SELECT key_check FROM lm_guard.identities WHERE principal_id=?',
                                  (identity.principal_id,)).fetchone()
            check = self._key_check(identity)
            if old and not hmac.compare_digest(old[0], check):
                raise PermissionError('identity key rebinding forbidden')
            self.db.execute('INSERT OR IGNORE INTO lm_guard.identities VALUES (?,?)',
                            (identity.principal_id, check))

    def authenticate(self, identity):
        if type(identity) is not LocalIdentity:
            raise PermissionError('authenticated fixture identity required')
        if self.db.execute('SELECT 1 FROM lm_guard.revoked_identities WHERE principal_id=?',
                           (identity.principal_id,)).fetchone():
            raise PermissionError('revoked fixture identity')
        old = self.db.execute('SELECT key_check FROM lm_guard.identities WHERE principal_id=?',
                              (identity.principal_id,)).fetchone()
        if not old or not hmac.compare_digest(old[0], self._key_check(identity)):
            raise PermissionError('unknown identity or wrong key')

    def revoke_identity(self, principal_id):
        self.authenticate(self.operator)
        fixture_id(principal_id)
        if principal_id == self.operator.principal_id:
            raise ValueError('operator trust-root replacement is unsupported')
        if not self.db.execute('SELECT 1 FROM lm_guard.identities WHERE principal_id=?', (principal_id,)).fetchone():
            raise ValueError('unknown identity')
        with self.engine.transaction():
            self.db.execute('INSERT OR IGNORE INTO lm_guard.revoked_identities VALUES (?)', (principal_id,))

    def upgrade_fixture(self):
        """Only the marked fixture can migrate v1 -> v2; no external DB import."""
        self.authenticate(self.operator)
        version = self._meta('version')
        if version == '2': return
        if version != '1': raise ValueError('unsupported migration')
        with self.engine.transaction():
            self.db.execute('''CREATE TABLE lm_obligations (
                obligation_id TEXT PRIMARY KEY, opaque_gene TEXT NOT NULL,
                kind TEXT NOT NULL, status TEXT NOT NULL)''')
            self.db.execute('''CREATE TABLE lm_observations (
                gene_id TEXT PRIMARY KEY REFERENCES lm_genes(gene_id),
                split TEXT NOT NULL, x INTEGER UNIQUE NOT NULL, y INTEGER NOT NULL)''')
            self.db.execute("UPDATE lm_meta SET value='2' WHERE key='version'")
            self.reconcile_guard()

    def set_policy(self, revision, *, privacy=('public',)):
        self.authenticate(self.operator)
        if type(revision) is not int:
            raise ValueError('policy revision must increase')
        privacy = sorted(_labels(privacy))
        if not privacy or set(privacy)-{'public','personal','private','sensitive'}:
            raise ValueError('invalid explicit privacy policy')
        body = dict(schema=SCHEMA, revision=revision, privacy=privacy,
                    authority='FIXTURE_ONLY', max_consent_ttl=3600)
        digest = commitment('living-memory.policy.v1', body)
        with self.engine.transaction():
            self.authenticate(self.operator)
            if revision <= int(self._guard('policy_revision')):
                raise ValueError('policy revision must increase')
            self.db.execute("UPDATE lm_guard.meta SET value=? WHERE key='policy_revision'", (str(revision),))
            self.db.execute("UPDATE lm_guard.meta SET value=? WHERE key='policy_json'", (_json(body),))
        return digest

    def policy(self):
        body = json.loads(self._guard('policy_json'))
        if body is None: raise PermissionError('policy unknown')
        return body, commitment('living-memory.policy.v1', body)

    def _gene(self, gid):
        fixture_id(gid)
        row = self.db.execute('SELECT * FROM lm_genes WHERE gene_id=?', (gid,)).fetchone()
        if row is None: raise ValueError('unknown gene')
        return row

    def add_gene(self, gid, meaning, metadata, token, *, parents=()):
        fixture_id(gid)
        if type(token) is not MemoryToken or token.token_id != fixture_id(token.token_id):
            raise ValueError('typed source token required')
        for value in asdict(token).values(): _label(value)
        fixture_id(token.source_instance)
        if not token.source_system or metadata.get('gene_id') != gid:
            raise ValueError('source identity or gene identity mismatch')
        if type(meaning) is not str or not meaning.strip() or len(meaning) > 512:
            raise ValueError('bounded synthetic meaning required')
        canonical(meaning)
        preview([metadata], metadata['project'], [], limit=0)
        parents = sorted(_labels(parents))
        if len(self.db.execute('SELECT gene_id FROM lm_genes').fetchall()) >= 256:
            raise ValueError('fixture gene budget')
        with self.engine.transaction():
            if self.block_action(gid): raise PermissionError('withdrawn identity cannot reenter')
            if self._source_blocked(asdict(token)):
                raise PermissionError('forgotten native source cannot reenter')
            parent_memories = []
            for parent in parents:
                row = self._gene(parent)
                if row['state'] != 'active' or self.block_action(parent):
                    raise PermissionError('held ancestry')
                if json.loads(row['metadata_json'])['project'] != metadata['project']:
                    raise PermissionError('cross-project ancestry')
                parent_memories.append(row['memory_id'])
            source_json = _json(asdict(token))
            prior = self.db.execute('SELECT source_json FROM lm_tokens WHERE token_id=?', (token.token_id,)).fetchone()
            if prior and prior[0] != source_json:
                raise ValueError('source token identity rebinding')
            self.db.execute('INSERT OR IGNORE INTO lm_tokens VALUES (?,?)', (token.token_id, source_json))
            mid = self.engine._enter(self._meta('blob'), meaning, 'fixture:source-token',
                                     parent_memories[0] if parent_memories else None)
            self.db.execute('INSERT INTO lm_genes VALUES (?,?,?,?,1,?)',
                            (gid, mid, token.token_id, _json(metadata), 'active'))
            self.db.executemany('INSERT INTO lm_lineage VALUES (?,?)', ((gid,p) for p in parents))
        return MemoryGene(gid, mid, token.token_id, 1, 'active')

    def catalog(self):
        genes = [json.loads(r[0]) for r in self.db.execute(
            "SELECT metadata_json FROM lm_genes WHERE state!='deleted' ORDER BY gene_id")]
        groups = []
        for row in self.db.execute('SELECT * FROM lm_chromosomes ORDER BY chromosome_id'):
            members = [r[0] for r in self.db.execute('''SELECT gene_id FROM lm_memberships
                WHERE chromosome_id=? ORDER BY gene_id''', (row['chromosome_id'],))]
            groups.append(dict(chromosome_id=row['chromosome_id'], project=row['project'],
                               parent_id=row['parent_id'], gene_ids=members))
        return genes, groups

    def add_chromosome(self, chromosome):
        if type(chromosome) is not MemoryChromosome: raise ValueError('typed chromosome required')
        candidate = asdict(chromosome)
        candidate['gene_ids'] = list(candidate['gene_ids'])
        genes, groups = self.catalog()
        # Unassigned genes get temporary validation-only groups, never persisted.
        claimed = {g for c in groups+[candidate] for g in c['gene_ids']}
        tmp = [dict(chromosome_id='fixture:unassigned:'+str(i), project=g['project'],
                    parent_id=None, gene_ids=[g['gene_id']])
               for i,g in enumerate(genes) if g['gene_id'] not in claimed]
        chromosome_preview(genes, groups+[candidate]+tmp, chromosome.chromosome_id,
                            chromosome.project, [], limit=0)
        with self.engine.transaction():
            self.db.execute('INSERT INTO lm_chromosomes VALUES (?,?,?)',
                (chromosome.chromosome_id, chromosome.project, chromosome.parent_id))
            self.db.executemany('INSERT INTO lm_memberships VALUES (?,?)',
                                ((chromosome.chromosome_id,g) for g in chromosome.gene_ids))

    def _context(self, context):
        if type(context) is not Context: raise ValueError('typed context required')
        for value in (context.project, context.app, context.purpose): _label(value)
        tags = sorted(_labels(context.tags))
        if context.destination is not None: fixture_id(context.destination)
        return dict(project=context.project, app=context.app, purpose=context.purpose,
                    tags=tags, destination=context.destination)

    def grant(self, gid, identity, context, operation, *, now, expires_at):
        self.authenticate(self.operator)
        self.authenticate(identity)
        _epoch(now); _epoch(expires_at)
        if operation not in OPERATIONS or not 0 < expires_at-now <= 3600:
            raise ValueError('invalid operation or consent lifetime')
        scope = self._context(context)
        if operation == 'transfer' and scope['destination'] is None:
            raise ValueError('explicit destination required for transfer')
        with self.engine.transaction():
            self.authenticate(self.operator)
            self.authenticate(identity)
            row = self._gene(gid)
            if row['state'] != 'active' or self.block_action(gid): raise PermissionError('held gene')
            metadata = json.loads(row['metadata_json'])
            if metadata['project'] != scope['project']: raise PermissionError('consent project mismatch')
            _, policy = self.policy()
            cid = _new()
            self.db.execute('INSERT INTO lm_consents VALUES (?,?,?,?,?,?,?,?,?,0)',
                (cid,gid,identity.principal_id,_json(scope),operation,policy,row['revision'],now,expires_at))
        return ConsentRecord(cid,gid,identity.principal_id,operation,policy,expires_at)

    def withdraw_consent(self, consent_id):
        self.authenticate(self.operator)
        with self.engine.transaction():
            row = self.db.execute('SELECT 1 FROM lm_consents WHERE consent_id=?', (consent_id,)).fetchone()
            if row is None: raise ValueError('unknown consent')
            self.db.execute('INSERT OR IGNORE INTO lm_guard.withdrawals VALUES (?)', (consent_id,))
            self.db.execute('UPDATE lm_consents SET withdrawn=1 WHERE consent_id=?', (consent_id,))

    def _reason(self, gid, principal, scope, operation, now, expected_policy):
        row = self._gene(gid)
        if self.block_action(gid) or row['state'] != 'active': return 'lifecycle_hold'
        policy_body, policy = self.policy()
        if policy != expected_policy: return 'stale_policy'
        metadata = json.loads(row['metadata_json'])
        if metadata['project'] != scope['project']: return 'scope_mismatch'
        if metadata['privacy'] not in policy_body['privacy']: return 'privacy_hold'
        if metadata['consent'] == 'never_infer': return 'never_infer'
        consents = self.db.execute('''SELECT consent_id,not_before,expires_at FROM lm_consents
            WHERE gene_id=? AND principal_id=? AND context_json=? AND operation=?
            AND policy_sha256=? AND gene_revision=? AND withdrawn=0''',
            (gid,principal,_json(scope),operation,policy,row['revision'])).fetchall()
        if not any(c['not_before'] <= now < c['expires_at'] and not self.db.execute(
            'SELECT 1 FROM lm_guard.withdrawals WHERE consent_id=?', (c['consent_id'],)).fetchone()
                   for c in consents): return 'consent_missing_or_expired'
        # An explicit consent receipt resolves ask-first; preserve every other gate.
        candidate = dict(metadata, privacy='public', consent='safe_to_use')
        result = preview([candidate], scope['project'], scope['tags'], limit=1)
        return None if result['eligible_ids'] else result['decisions'][0]['reason']

    def evaluate(self, ids, identity, context, operation, *, now, expected_policy):
        self.authenticate(identity)
        _epoch(now)
        if operation not in OPERATIONS: raise ValueError('action authority unsupported')
        scope = self._context(context)
        ids = sorted(_labels(ids))
        if len(ids) > 9: raise ValueError('expression budget exceeded')
        admitted, held = [], []
        with self.engine.transaction():
            self.authenticate(identity)
            for gid in ids:
                reason = self._reason(gid,identity.principal_id,scope,operation,now,expected_policy)
                (held if reason else admitted).append((gid,reason) if reason else gid)
            event = ExpressionEvent(_new(),tuple(admitted),tuple(held),expected_policy,operation)
            evidence = {gid:self._gene(gid)['token_id'] for gid in admitted}
            body = dict(event_id=event.event_id, admitted_ids=admitted, held=[list(x) for x in held],
                        policy_sha256=expected_policy, operation=operation, principal=identity.principal_id,
                        context=scope, now=now, evidence=evidence, authority='FIXTURE_ONLY')
            self.db.execute('INSERT INTO lm_events VALUES (?,?,?)', (event.event_id,'expression',_json(body)))
        return event

    def opaque(self, value):
        return hmac.new(self.operator.key, (self._meta('store_id')+'\0'+value).encode(),
                        hashlib.sha256).hexdigest()

    def block_action(self, gid):
        row = self.db.execute('SELECT action FROM lm_guard.blocks WHERE opaque_id=?',
                              (self.opaque(gid),)).fetchone()
        return row[0] if row else None

    def _source_guard_id(self, source):
        # Token ID and revision are deliberately excluded: a new local token
        # or newer revision must not silently reactivate the same native row.
        identity = [source[k] for k in ('source_system', 'source_instance', 'native_id')]
        return self.opaque('living-memory.source-forget.v1\0'+_json(identity))

    def _source_blocked(self, source):
        return self.db.execute('SELECT 1 FROM lm_guard.blocks WHERE opaque_id=?',
                               (self._source_guard_id(source),)).fetchone() is not None

    def _scrub(self, gid):
        row = self._gene(gid)
        # Preserve a keyed, store-scoped reimport guard before scrubbing source
        # metadata. This shares the existing atomic main/guard transaction.
        if row['token_id']:
            source = self.db.execute('SELECT source_json FROM lm_tokens WHERE token_id=?',
                                     (row['token_id'],)).fetchone()
            if source is None:
                raise ValueError('missing source token during forget')
            self.db.execute('INSERT OR IGNORE INTO lm_guard.blocks VALUES (?,?)',
                            (self._source_guard_id(json.loads(source[0])), 'forget'))
        marker = '[deleted synthetic fixture '+row['memory_id']+']'
        mid = row['memory_id']
        fingerprint = _digest(marker)
        memory = self.engine.memory(mid)
        marker_matches = (memory['content'] == marker and memory['fingerprint'] == fingerprint
                          and memory['source_ref'] is None and memory['status'] == 'retired')
        events = self.engine.events(mid)
        # A tombstone is not sufficient evidence that all cleanup is complete.
        # Preserve the existing deletion event only if its marker and sole
        # event already match. Continue sweeping all dependent artifacts.
        event_matches = (len(events) == 1 and events[0]['stage'] == 'DEATH'
                         and events[0]['detail'] == {'reason': 'fixture logical deletion'})
        if not marker_matches:
            self.db.execute('UPDATE memories SET content=?,fingerprint=?,source_ref=NULL,status=? WHERE id=?',
                            (marker,fingerprint,'retired',mid))
        self.db.execute('''UPDATE memories SET parent_memory_id=NULL
            WHERE (id=? AND parent_memory_id IS NOT NULL) OR parent_memory_id=?''', (mid,mid))
        if not (marker_matches and event_matches):
            self.db.execute('DELETE FROM events WHERE memory_id=?', (mid,))
            self.engine._event(mid,'DEATH',reason='fixture logical deletion')
        self.db.execute('DELETE FROM lm_copies WHERE gene_id=?', (gid,))
        self.db.execute('DELETE FROM lm_consents WHERE gene_id=?', (gid,))
        if self._meta('version') == '2':
            self.db.execute('DELETE FROM lm_observations WHERE gene_id=?', (gid,))
        self.db.execute('DELETE FROM lm_memberships WHERE gene_id=?', (gid,))
        self.db.execute('DELETE FROM lm_lineage WHERE child_id=? OR parent_id=?', (gid,gid))
        metadata = _json({'gene_id':gid})
        if row['token_id'] is not None or row['metadata_json'] != metadata or row['state'] != 'deleted':
            self.db.execute('UPDATE lm_genes SET token_id=NULL,metadata_json=?,state=? WHERE gene_id=?',
                            (metadata, 'deleted', gid))
        if row['token_id']:
            self.db.execute('''DELETE FROM lm_tokens WHERE token_id=? AND NOT EXISTS
                (SELECT 1 FROM lm_genes WHERE token_id=?)''', (row['token_id'],row['token_id']))
        # IDs are fresh opaque fixture IDs. Remove old event references, rather
        # than retaining hashes of deleted source text in ordinary lineage.
        def references(value):
            if type(value) is str: return value == gid
            if type(value) is list: return any(references(v) for v in value)
            if type(value) is dict: return gid in value or any(references(v) for v in value.values())
            return False
        removed_events = set()
        for event in self.db.execute('SELECT event_id,body_json FROM lm_events').fetchall():
            if references(json.loads(event['body_json'])):
                removed_events.add(event['event_id'])
                self.db.execute('DELETE FROM lm_events WHERE event_id=?', (event['event_id'],))
        # Packet receipts may indirectly refer to deleted events. Clear local
        # receipt bodies for affected events; retain unrelated receipt lineage.
        # The separate guard keeps only keyed replay checks.
        for receipt in self.db.execute('SELECT replay_id,body_json FROM lm_receipts').fetchall():
            if json.loads(receipt['body_json'])['body']['evidence_event'] in removed_events:
                self.db.execute('DELETE FROM lm_receipts WHERE replay_id=?', (receipt['replay_id'],))

    def reconcile_guard(self):
        with self.engine.transaction():
            for row in self.db.execute('SELECT gene_id,state FROM lm_genes').fetchall():
                action = self.block_action(row['gene_id'])
                if action == 'forget': self._scrub(row['gene_id'])
                elif action:
                    # A guard block applies to every dependent; it cannot identify
                    # the original repair target after a stale main-only restore.
                    # Preserve a locally recorded matching terminal state, but
                    # never manufacture one or relax the guard's denial.
                    terminal = {'retire': 'retired', 'correct': 'superseded',
                                'supersede': 'superseded'}.get(action)
                    if row['state'] != 'held' and (terminal is None or row['state'] != terminal):
                        self.db.execute("UPDATE lm_genes SET state='held' WHERE gene_id=?", (row['gene_id'],))
                if action: self._ensure_obligations(row['gene_id'])
            self.db.execute('''UPDATE lm_consents SET withdrawn=1 WHERE withdrawn!=1 AND consent_id IN
                               (SELECT consent_id FROM lm_guard.withdrawals)''')

    def _ensure_obligations(self, gid):
        if self._meta('version') != '2': return
        for kind in ('recipient_copies','source_store','backups','physical_media'):
            if not self.db.execute('SELECT 1 FROM lm_obligations WHERE opaque_gene=? AND kind=?',
                                   (self.opaque(gid),kind)).fetchone():
                self.db.execute('INSERT INTO lm_obligations VALUES (?,?,?,?)',
                    (_new(),self.opaque(gid),kind,'UNKNOWN_EXTERNAL_COVERAGE'))

    def repair(self, target, action, *, replacement=None):
        self.authenticate(self.operator)
        if self._meta('version') != '2': raise ValueError('fixture migration to v2 required')
        if action not in {'correct','supersede','retire','revoke','forget'}:
            raise ValueError('unsupported repair action')
        if action in {'correct','supersede'}:
            row = self._gene(replacement)
            if row['state'] != 'active' or replacement == target or self.block_action(replacement):
                raise ValueError('fresh active replacement required')
        elif replacement is not None: raise ValueError('unexpected replacement')
        with self.engine.transaction():
            original = self._gene(target)
            if original['state'] == 'deleted': raise ValueError('already deleted')
            affected = [r[0] for r in self.db.execute('''WITH RECURSIVE affected(gene_id) AS (
                SELECT gene_id FROM lm_genes WHERE gene_id=? UNION
                SELECT child_id FROM lm_lineage JOIN affected ON parent_id=affected.gene_id)
                SELECT gene_id FROM affected ORDER BY gene_id''', (target,))]
            if replacement in affected: raise ValueError('replacement depends on withdrawn ancestry')
            if replacement:
                if json.loads(self._gene(replacement)['metadata_json'])['project'] != json.loads(original['metadata_json'])['project']:
                    raise ValueError('cross-project replacement')
            for gid in affected:
                prior = self.block_action(gid)
                if prior != 'forget':
                    self.db.execute('INSERT OR REPLACE INTO lm_guard.blocks VALUES (?,?)',
                                    (self.opaque(gid),action))
                self.db.execute("UPDATE lm_genes SET state='held' WHERE gene_id=?", (gid,))
                self.db.execute('DELETE FROM lm_copies WHERE gene_id=?', (gid,))
                self.db.execute('UPDATE lm_consents SET withdrawn=1 WHERE gene_id=?', (gid,))
                self._ensure_obligations(gid)
                if action == 'forget': self._scrub(gid)
            state = {'correct':'superseded','supersede':'superseded','retire':'retired',
                     'revoke':'held','forget':'deleted'}[action]
            self.db.execute('UPDATE lm_genes SET state=? WHERE gene_id=?', (state,target))
            event = RepairEvent(_new(),action,tuple(affected))
            # Deletion evidence is separate and has no raw memory IDs or payload commitments.
            if action != 'forget':
                self.db.execute('INSERT INTO lm_events VALUES (?,?,?)', (event.event_id,'repair',
                    _json(dict(event_id=event.event_id,action=action,affected_ids=affected,replacement=replacement))))
        return event

    def add_copy(self, gid, kind, content):
        if kind not in {'index','cache','export'}: raise ValueError('unsupported fixture copy')
        canonical(content)
        with self.engine.transaction():
            if self._gene(gid)['state'] != 'active' or self.block_action(gid):
                raise PermissionError('held gene')
            cid = _new()
            self.db.execute('INSERT INTO lm_copies VALUES (?,?,?,?)', (cid,gid,kind,content))
        return cid

    def reconstruct(self):
        """Metadata state only; explicit inspection inside the trusted fixture."""
        genes = [dict(r) for r in self.db.execute('SELECT * FROM lm_genes ORDER BY gene_id')]
        return dict(schema=SCHEMA,version=int(self._meta('version')),genes=genes,
                    lineage=[list(r) for r in self.db.execute('SELECT * FROM lm_lineage ORDER BY child_id,parent_id')],
                    groups=self.catalog()[1], engine_integrity=self.engine.verify()['ok'])
