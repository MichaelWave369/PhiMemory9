"""Disposable databases only. Positive, adversarial, rollback and cold-start checks."""
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from phimemory9.living_contract import (LocalIdentity, MemoryToken, MemoryChromosome,
    Context, canonical, commitment, strict_loads)
from phimemory9.living_store import LivingStore
from phimemory9.living_transport import pack, admit, verify_receipt, _mac
from phimemory9.living_learning import observe, learn
from phimemory9 import living_geometry as geometry

OWNER = LocalIdentity('fixture:operator', b'o'*32)
SENDER = LocalIdentity('fixture:sender', b's'*32)
DEST = LocalIdentity('fixture:receiver', b'd'*32)
CONTEXT = Context('demo','demo-app','research',('research',))


def metadata(gid, **changes):
    return dict(dict(gene_id=gid,project='demo',privacy='public',consent='ask_first',
        repair='clean',confidence='high',claim='fact',source_refs=['fixture:source'],
        activate=['research'],suppress=[]), **changes)


def token(name):
    return MemoryToken('fixture:token:'+name,'synthetic','fixture:source',name,'fixture:v1')


class LivingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'memory.sqlite3'
        self.guard = Path(self.tmp.name)/'guard.sqlite3'
        self.store = LivingStore.create(self.path,self.guard,OWNER)
        self.store.register_identity(SENDER)
        self.store.register_identity(DEST)
        self.policy = self.store.set_policy(1)
        self.gid = 'fixture:a'
        self.store.add_gene(self.gid,'invented initial observation',metadata(self.gid),token('a'))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def allow(self, gid=None, context=CONTEXT, operation='express', **kwargs):
        return self.store.grant(gid or self.gid,SENDER,context,operation,
                                now=kwargs.get('now',100),expires_at=kwargs.get('expires_at',200))

    def evaluate(self, context=CONTEXT, **kwargs):
        return self.store.evaluate([self.gid],SENDER,context,kwargs.get('operation','express'),
                                  now=kwargs.get('now',150),expected_policy=kwargs.get('policy',self.policy))

    def reopen(self):
        self.store.close()
        self.store = LivingStore.open(self.path,self.guard,OWNER)

    def test_atomic_creation_and_shared_token(self):
        before = self.store.reconstruct()
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.engine.transaction():
                self.store.add_gene('fixture:b','new content',metadata('fixture:b'),token('b'))
                self.store.add_gene(self.gid,'duplicate id',metadata(self.gid),token('z'))
        self.assertEqual(before,self.store.reconstruct())
        self.store.add_gene('fixture:c','different meaning',metadata('fixture:c'),token('a'))
        self.store.repair(self.gid,'forget')
        self.assertEqual(self.store._gene('fixture:c')['state'],'active')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM lm_tokens').fetchone()[0],1)

    def test_reconstruction_and_many_to_many_membership(self):
        self.store.add_chromosome(MemoryChromosome('root','demo',None,(self.gid,)))
        self.store.add_chromosome(MemoryChromosome('child','demo','root',(self.gid,)))
        before = self.store.reconstruct()
        self.reopen()
        self.assertEqual(before,self.store.reconstruct())
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM lm_memberships').fetchone()[0],2)
        self.assertNotEqual(self.store._gene(self.gid)['memory_id'],self.gid)

    def test_no_existing_store_migration_and_unknown_version(self):
        with self.assertRaises(FileExistsError): LivingStore.create(self.path,self.guard,OWNER)
        self.store.db.execute("UPDATE lm_meta SET value='999' WHERE key='version'")
        self.store.db.commit()
        with self.assertRaises(ValueError): LivingStore.open(self.path,self.guard,OWNER)

    def test_explicit_fixture_schema_upgrade(self):
        p,g=Path(self.tmp.name)/'old.sqlite3',Path(self.tmp.name)/'old-guard.sqlite3'
        with LivingStore.create(p,g,OWNER,version=1) as old:
            self.assertEqual(old._meta('version'),'1')
            old.upgrade_fixture()
            self.assertEqual(old._meta('version'),'2')
        with LivingStore.open(p,g,OWNER) as current:
            self.assertTrue(current.reconstruct()['engine_integrity'])

    def test_missing_consent_then_persisted_expression(self):
        self.assertEqual(self.evaluate().held[0][1],'consent_missing_or_expired')
        self.allow()
        event=self.evaluate()
        self.assertEqual(event.admitted_ids,(self.gid,))
        record=self.store.db.execute('SELECT body_json FROM lm_events WHERE event_id=?',(event.event_id,)).fetchone()
        self.assertEqual(json.loads(record[0])['evidence'][self.gid],token('a').token_id)
        self.reopen()
        self.assertEqual(self.evaluate().admitted_ids,(self.gid,))

    def test_no_action_or_implicit_transfer(self):
        self.allow()
        self.assertFalse(self.evaluate(operation='transfer').admitted_ids)
        with self.assertRaises(ValueError): self.evaluate(operation='execute')

    def test_expiry_and_context_boundaries(self):
        self.allow()
        for changed in (replace(CONTEXT,project='other'),replace(CONTEXT,app='other'),
                        replace(CONTEXT,purpose='other'),replace(CONTEXT,tags=('other',))):
            self.assertFalse(self.evaluate(changed).admitted_ids)
        self.assertFalse(self.evaluate(now=99).admitted_ids)
        self.assertFalse(self.evaluate(now=200).admitted_ids)

    def test_suppression_privacy_and_unknown_policy(self):
        self.store.add_gene('fixture:s','suppressed',metadata('fixture:s',suppress=['research']),token('s'))
        self.allow('fixture:s')
        result=self.store.evaluate(['fixture:s'],SENDER,CONTEXT,'express',now=150,expected_policy=self.policy)
        self.assertEqual(result.held,(('fixture:s','suppression_match'),))
        self.store.add_gene('fixture:p','private',metadata('fixture:p',privacy='private'),token('p'))
        self.allow('fixture:p')
        result=self.store.evaluate(['fixture:p'],SENDER,CONTEXT,'express',now=150,expected_policy=self.policy)
        self.assertEqual(result.held,(('fixture:p','privacy_hold'),))
        self.allow()
        self.assertEqual(self.evaluate(policy='0'*64).held[0][1],'stale_policy')

    def test_policy_revision_invalidates_old_consent_and_restored_main(self):
        self.allow()
        snapshot=Path(self.tmp.name)/'backup.sqlite3'
        shutil.copyfile(self.path,snapshot)
        new_policy=self.store.set_policy(2)
        self.assertFalse(self.evaluate().admitted_ids)
        self.assertFalse(self.evaluate(policy=new_policy).admitted_ids)
        self.store.close()
        shutil.copyfile(snapshot,self.path)
        self.store=LivingStore.open(self.path,self.guard,OWNER)
        self.assertFalse(self.evaluate().admitted_ids)
        self.assertEqual(self.store.policy()[1],new_policy)

    def test_consent_withdrawal_survives_main_restore(self):
        consent=self.allow()
        snapshot=Path(self.tmp.name)/'backup.sqlite3'
        shutil.copyfile(self.path,snapshot)
        self.store.withdraw_consent(consent.consent_id)
        self.assertFalse(self.evaluate().admitted_ids)
        self.store.close(); shutil.copyfile(snapshot,self.path)
        self.store=LivingStore.open(self.path,self.guard,OWNER)
        self.assertFalse(self.evaluate().admitted_ids)

    def test_identity_authentication_and_rebinding(self):
        with self.assertRaises(PermissionError):
            self.store.evaluate([self.gid],LocalIdentity(SENDER.principal_id,b'x'*32),CONTEXT,
                                'express',now=150,expected_policy=self.policy)
        with self.assertRaises(PermissionError):
            self.store.register_identity(LocalIdentity(SENDER.principal_id,b'x'*32))

    def test_cross_scope_ancestry_and_source_rebinding_refused(self):
        with self.assertRaises(PermissionError):
            self.store.add_gene('fixture:x','cross scope',metadata('fixture:x',project='other'),
                                token('x'),parents=[self.gid])
        with self.assertRaises(ValueError):
            self.store.add_gene('fixture:r','rebound',metadata('fixture:r'),replace(token('a'),native_id='other'))

    def packet(self):
        context=replace(CONTEXT,destination=DEST.principal_id)
        self.allow(context=context,operation='transfer')
        return pack(self.store,[self.gid],SENDER,DEST,context,now=150,expires_at=190,expected_policy=self.policy)

    def test_authenticated_packet_and_restart_idempotency(self):
        packet=self.packet()
        first=admit(self.store,packet,SENDER,DEST,now=151)
        self.assertTrue(verify_receipt(first,DEST))
        self.reopen()
        self.assertEqual(first,admit(self.store,packet,SENDER,DEST,now=152))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM lm_guard.replays').fetchone()[0],1)

    def test_tampered_packet_wrong_destination_expiry_and_policy(self):
        packet=self.packet()
        tampered=copy.deepcopy(packet);tampered['body']['purpose']='other'
        with self.assertRaises(PermissionError): admit(self.store,tampered,SENDER,DEST,now=151)
        other=LocalIdentity('fixture:other',b'x'*32);self.store.register_identity(other)
        with self.assertRaises(PermissionError): admit(self.store,packet,SENDER,other,now=151)
        with self.assertRaises(PermissionError): admit(self.store,packet,SENDER,DEST,now=190)
        self.store.set_policy(2)
        with self.assertRaises(PermissionError): admit(self.store,packet,SENDER,DEST,now=151)

    def test_authenticated_receipt_substitution_refused(self):
        packet=self.packet()
        expressed=self.evaluate().event_id
        packet['body']['evidence_event']=expressed
        packet['mac']=_mac(SENDER.key,packet['body'])
        with self.assertRaisesRegex(PermissionError,'receipt lineage'):
            admit(self.store,packet,SENDER,DEST,now=151)

    def test_replay_conflict_and_consent_recheck(self):
        packet=self.packet()
        admit(self.store,packet,SENDER,DEST,now=151)
        altered=copy.deepcopy(packet);altered['body']['expires_at']-=1
        altered['mac']=_mac(SENDER.key,altered['body'])
        with self.assertRaisesRegex(PermissionError,'reused packet'):
            admit(self.store,altered,SENDER,DEST,now=152)
        self.store.repair(self.gid,'revoke')
        with self.assertRaises(PermissionError): admit(self.store,packet,SENDER,DEST,now=152)

    def test_replay_guard_survives_database_restore(self):
        packet=self.packet()
        snapshot=Path(self.tmp.name)/'backup.sqlite3';shutil.copyfile(self.path,snapshot)
        admit(self.store,packet,SENDER,DEST,now=151)
        self.store.close();shutil.copyfile(snapshot,self.path)
        self.store=LivingStore.open(self.path,self.guard,OWNER)
        with self.assertRaisesRegex(PermissionError,'durable replay'):
            admit(self.store,packet,SENDER,DEST,now=152)

    def test_transitive_shared_ancestry_and_held_parent_refusal(self):
        self.store.add_gene('fixture:b','independent',metadata('fixture:b'),token('b'))
        self.store.add_gene('fixture:child','joint',metadata('fixture:child'),token('c'),parents=[self.gid,'fixture:b'])
        affected=self.store.repair(self.gid,'revoke').affected_ids
        self.assertEqual(set(affected),{self.gid,'fixture:child'})
        self.assertEqual(self.store._gene('fixture:b')['state'],'active')
        with self.assertRaises(PermissionError):
            self.store.add_gene('fixture:new','resurrection',metadata('fixture:new'),token('n'),parents=[self.gid])

    def test_interrupted_repair_rolls_back_store_and_guard(self):
        self.allow()
        self.store.db.execute('''CREATE TRIGGER interrupt_repair BEFORE INSERT ON lm_events
                                WHEN NEW.kind='repair' BEGIN SELECT RAISE(ABORT,'fixture interruption'); END''')
        self.store.db.commit()
        with self.assertRaises(sqlite3.IntegrityError): self.store.repair(self.gid,'revoke')
        self.assertIsNone(self.store.block_action(self.gid))
        self.assertEqual(self.evaluate().admitted_ids,(self.gid,))

    def test_distinct_correction_retirement_and_content_deletion(self):
        self.store.add_gene('fixture:replacement','corrected meaning',metadata('fixture:replacement'),token('r'))
        self.store.repair(self.gid,'correct',replacement='fixture:replacement')
        self.assertEqual(self.store._gene(self.gid)['state'],'superseded')
        self.assertEqual(self.store._gene('fixture:replacement')['state'],'active')
        self.store.repair('fixture:replacement','retire')
        self.assertIn('corrected meaning',self.store.engine.memory(self.store._gene('fixture:replacement')['memory_id'])['content'])
        self.store.repair(self.gid,'forget')
        dump='\n'.join(self.store.db.iterdump())
        self.assertNotIn('invented initial observation',dump)
        self.assertEqual(self.store._gene(self.gid)['state'],'deleted')
        self.assertTrue(self.store.engine.verify()['ok'])

    def test_forget_copies_and_backup_reconciliation(self):
        self.allow()
        for kind in ('index','cache','export'):
            self.store.add_copy(self.gid,kind,'invented initial observation')
        snapshot=Path(self.tmp.name)/'backup.sqlite3';shutil.copyfile(self.path,snapshot)
        self.store.repair(self.gid,'forget')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM lm_copies').fetchone()[0],0)
        self.store.close();shutil.copyfile(snapshot,self.path)
        self.store=LivingStore.open(self.path,self.guard,OWNER)
        self.assertEqual(self.store._gene(self.gid)['state'],'deleted')
        self.assertNotIn('invented initial observation','\n'.join(self.store.db.iterdump()))
        self.assertFalse(self.evaluate().admitted_ids)
        # Unknown external copies remain obligations, never a verified-erasure claim.
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM lm_obligations').fetchone()[0],4)

    def test_identity_revocation_is_durable_and_cannot_reactivate(self):
        self.allow()
        self.store.revoke_identity(SENDER.principal_id)
        self.reopen()
        with self.assertRaises(PermissionError): self.evaluate()
        with self.assertRaises(PermissionError): self.store.register_identity(SENDER)
        with self.assertRaises(ValueError): self.store.revoke_identity(OWNER.principal_id)

    def test_interrupted_deletion_is_atomic(self):
        self.store.add_copy(self.gid,'cache','invented initial observation')
        self.store.db.execute('''CREATE TRIGGER interrupt_delete BEFORE UPDATE ON lm_genes
            WHEN NEW.state='deleted' BEGIN SELECT RAISE(ABORT,'deletion interruption'); END''')
        self.store.db.commit()
        with self.assertRaises(sqlite3.IntegrityError): self.store.repair(self.gid,'forget')
        self.assertIsNone(self.store.block_action(self.gid))
        self.assertEqual(self.store._gene(self.gid)['state'],'active')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM lm_copies').fetchone()[0],1)
        self.assertIn('invented initial observation','\n'.join(self.store.db.iterdump()))

    def test_forgetting_does_not_match_unrelated_id_prefixes(self):
        other='fixture:ab'
        self.store.add_gene(other,'unrelated prefix',metadata(other),token('ab'))
        self.allow(other)
        event=self.store.evaluate([other],SENDER,CONTEXT,'express',now=150,expected_policy=self.policy)
        self.store.repair(self.gid,'forget')
        self.assertIsNotNone(self.store.db.execute('SELECT 1 FROM lm_events WHERE event_id=?',(event.event_id,)).fetchone())

    def lattice(self):
        self.store.add_chromosome(MemoryChromosome('root','demo',None,(self.gid,)))
        self.store.add_chromosome(MemoryChromosome('child','demo','root',(self.gid,)))
        pockets=[dict(pocket_id='pocket:root',parent_id=None,project='demo',chromosome_ids=['root']),
                 dict(pocket_id='pocket:child',parent_id='pocket:root',project='demo',chromosome_ids=['child'])]
        return geometry.snapshot(self.store,pockets)

    def test_nested_flat_roundtrip_preserves_native_identity_and_shared_refs(self):
        flat=self.lattice()
        self.assertEqual(geometry.flatten(geometry.nest(flat)),flat)
        self.assertEqual(len(flat['genes']),1)
        self.assertEqual(len(flat['chromosomes']),2)
        self.assertEqual(flat['sources'][0]['token']['native_id'],'a')
        reordered=copy.deepcopy(flat)
        reordered['pockets'].reverse();reordered['chromosomes'].reverse()
        self.assertEqual(geometry.validate(reordered),flat)

    def test_geometry_unknown_parent_cycle_scope_and_loss_refused(self):
        flat=self.lattice()
        for fault in ('unknown','cycle','scope','lost_source','lost_membership'):
            bad=copy.deepcopy(flat)
            if fault=='unknown':bad['pockets'][0]['parent_id']='missing'
            if fault=='cycle':bad['pockets'][0]['parent_id']=bad['pockets'][0]['pocket_id']
            if fault=='scope':bad['pockets'][0]['project']='other'
            if fault=='lost_source':bad['sources']=[]
            if fault=='lost_membership':bad['pockets'][0]['chromosome_ids']=[]
            with self.assertRaises(ValueError):geometry.validate(bad)

    @unittest.skipUnless(shutil.which('node'),'Node runtime unavailable')
    def test_separate_node_geometry_and_canonical_conformance(self):
        flat=self.lattice()
        path=Path(self.tmp.name)/'geometry.json';path.write_bytes(canonical(flat))
        script=Path(__file__).resolve().parents[1]/'scripts/living_conformance.mjs'
        result=subprocess.run(['node',str(script),str(path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        checked=json.loads(result.stdout)
        self.assertEqual(checked['canonical'].encode(),canonical(flat))
        self.assertEqual(checked['sha256'],hashlib.sha256(canonical(flat)).hexdigest())

    def test_cold_process_reconstructs_and_refuses_wrong_key(self):
        self.store.repair(self.gid,'revoke')
        self.store.close()
        code='''from phimemory9.living_store import LivingStore
from phimemory9.living_contract import LocalIdentity
import sys
with LivingStore.open(sys.argv[1],sys.argv[2],LocalIdentity("fixture:operator",b"o"*32)) as s:
 assert s._gene("fixture:a")["state"]=="held"
 assert s.engine.verify()["ok"]
print("cold-restart-ok")
'''
        result=subprocess.run([sys.executable,'-c',code,str(self.path),str(self.guard)],capture_output=True,text=True)
        self.store=LivingStore.open(self.path,self.guard,OWNER)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('cold-restart-ok',result.stdout)
        with self.assertRaises(PermissionError):
            LivingStore.open(self.path,self.guard,LocalIdentity(OWNER.principal_id,b'x'*32))

    def test_governed_learning_reconstruction_and_withdrawal(self):
        # The common unobserved background root is not an observation.
        for x,split in enumerate(('train','train','train','audit','audit','test','test')):
            gid='fixture:o'+str(x)
            self.store.add_gene(gid,'observation '+str(x),metadata(gid),token('o'+str(x)))
            observe(self.store,gid,split,x,(7*x+4)%31)
            self.allow(gid,operation='learn')
        baseline=learn(self.store,SENDER,CONTEXT,now=150,expected_policy=self.policy)
        self.assertEqual((baseline['rule'],baseline['test_matches']),([7,4],2))
        self.reopen()
        restored=learn(self.store,SENDER,CONTEXT,now=150,expected_policy=self.policy)
        self.assertEqual(restored['rule'],baseline['rule'])
        self.store.repair('fixture:o0','revoke');self.store.repair('fixture:o1','revoke')
        held=learn(self.store,SENDER,CONTEXT,now=150,expected_policy=self.policy)
        self.assertIsNone(held['rule'])
        self.assertEqual(held['excluded_count'],2)
        self.store.repair('fixture:o2','forget')
        self.assertIsNone(self.store.db.execute('SELECT 1 FROM lm_observations WHERE gene_id=?',('fixture:o2',)).fetchone())


class CanonicalTests(unittest.TestCase):
    def test_types_duplicates_resource_bounds(self):
        for value in (1.0,float('nan'),2**53,'non-ascii\u03a6',{'a':(1,2)},'\x7f'):
            with self.assertRaises(ValueError): canonical(value)
        with self.assertRaises(ValueError): strict_loads('{"a":1,"a":2}')
        with self.assertRaises(ValueError): canonical('x'*2049)
        self.assertEqual(canonical({'b':1,'a':[True,None,'x']}),b'{"a":[true,null,"x"],"b":1}')
        for wire in ('{"a":1.0}','{"a":-0}',' {"a":1}'):
            with self.assertRaises(ValueError): strict_loads(wire)

    def test_frozen_literals_and_digests(self):
        path=Path(__file__).parent/'fixtures/living_canonical_v1.json'
        for vector in json.loads(path.read_text()):
            self.assertEqual(canonical(vector['value']).decode(),vector['canonical'])
            self.assertEqual(hashlib.sha256(canonical(vector['value'])).hexdigest(),vector['sha256'])

    def test_domain_and_information_loss_counterexamples(self):
        self.assertNotEqual(commitment('a',{'x':1}),commitment('b',{'x':1}))
        # Equal aggregate counts discard membership and cannot establish identity.
        a,b={'members':['fixture:a']},{'members':['fixture:b']}
        self.assertEqual(len(a['members']),len(b['members']))
        self.assertNotEqual(canonical(a),canonical(b))
