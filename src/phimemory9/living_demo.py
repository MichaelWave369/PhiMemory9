"""Reproducible disposable-fixture proof loop; every external boundary is HELD.

Optional native sources are explicit, operator-selected local checkouts.
Nothing is downloaded, dispatched or executed from a transported packet.
"""
import argparse
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

from .living_contract import LocalIdentity, MemoryToken, MemoryChromosome, Context, canonical
from .living_store import LivingStore
from .living_transport import pack, admit, verify_receipt
from .living_learning import observe, learn
from . import living_geometry as geometry
from . import genomememory_memoria as memoria
from . import genomememory_sml as sml
from .genomememory_relational import experiment
from .genomememory_retention import SCHEMA as RETENTION_SCHEMA, KINDS

BLOCKERS = ['real_source_security','external_identity_and_key_custody','external_independent_audit',
            'complete_copy_and_physical_erasure_coverage','guard_rollback_trust',
            'native_runtime_authority_mapping','unseen_real_world_evaluation']


def _metadata(gid):
    return dict(gene_id=gid,project='demo',privacy='public',consent='ask_first',repair='clean',
        confidence='high',claim='fact',source_refs=['fixture:explicit-invented-source'],
        activate=['research'],suppress=[])


def _token(name, system='synthetic', native_id=None, revision='fixture:v1'):
    return MemoryToken('fixture:token:'+name,system,'fixture:source',native_id or name,revision)


def _load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')


def _source_receipt(path):
    return dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def native_exports(out, memoria_source=None, sml_packets=None):
    results={};source_token=None
    if memoria_source:
        sys.path.insert(0,str(memoria_source))
        from db.genomememory_export import create_fixture, export_fixture_metadata
        from db.storage import store_memory, set_permission
        conn=create_fixture(out/'memoria-source.sqlite3','fixture:memoria')
        try:
            mid=store_memory(conn,dict(content='Synthetic source note, manually created for this experiment.',
                app_name='demo',agent_id='fixture:author',timestamp='2026-06-20T12:00:00+00:00',
                tags=['research'],importance_score=1,metadata={'inert':'never exported'}))
            denied=False
            try: export_fixture_metadata(conn,expected_app='demo',fixture_id='fixture:memoria')
            except PermissionError: denied=True
            set_permission(conn,'demo',True,False)
            snapshot=export_fixture_metadata(conn,expected_app='demo',fixture_id='fixture:memoria')
            stage=memoria.stage_snapshot(snapshot,'demo',memoria.review_snapshot(snapshot,'demo')['snapshot_sha256'])
            assert denied and stage['eligible_count']==0
            assert all(all(v is None for v in c['policy'].values()) for c in stage['candidates'])
            assert 'Synthetic source note' not in json.dumps(snapshot)
            source_token=_token('native-source','Memoria',str(mid),memoria.SOURCE_REVISION)
            results['memoria']=dict(executed=True,native_id=mid,denied_without_permission=denied,
                held_count=len(stage['candidates']),eligible_count=0,source_revision=memoria.SOURCE_REVISION,
                adapter_source=_source_receipt(memoria_source/'db/genomememory_export.py'))
        finally: conn.close()
    else: results['memoria']=dict(executed=False,reason='explicit_local_source_not_supplied')
    if sml_packets:
        module=_load('living_native_sml_packets',sml_packets)
        packet=module.MemoryPacket(payload='Synthetic native payload; excluded from projection.',
            author_agent_id='fixture:author',memory_id='fixture:sml-native',
            timestamp='2026-06-20T12:00:00+00:00',state='active',collab_state='shared_verified',
            proof_score=1,coherence_score=1,links=['fixture:unknown'],parent_ids=['fixture:ancestor'])
        projection={k:v for k,v in packet.to_dict().items() if k in sml.FIELDS}
        snapshot=dict(schema=sml.SCHEMA,synthetic=True,source_revision=sml.REVISION,
                      fixture_id='fixture:sml',packets=[projection])
        stage=sml.stage_snapshot(snapshot,'fixture:sml',sml.review_snapshot(snapshot,'fixture:sml')['snapshot_sha256'])
        assert stage['eligible_count']==0 and 'payload' not in projection
        candidate=stage['candidates'][0]
        assert candidate['unresolved_links']==['fixture:unknown']
        assert candidate['unresolved_parents']==['fixture:ancestor']
        assert all(v is None for v in candidate['policy'].values())
        results['sml']=dict(executed=True,native_id=packet.memory_id,state=packet.state,
            collab_state=packet.collab_state,held_count=1,eligible_count=0,scores_promoted=False,
            source_revision=sml.REVISION,packet_source=_source_receipt(sml_packets))
    else: results['sml']=dict(executed=False,reason='explicit_native_packet_source_not_supplied')
    _write(out/'native-exports.json',results)
    return results,source_token


def benchmark(out, native_genesis=None):
    """Nine authored affine relations, three repeated contexts; fixed criteria.

    54 predictions per method but only 18 distinct held-out relation/input pairs.
    Acquisitions, state reads, governance, validation and compute are separate.
    """
    out.mkdir()
    native=_load('living_native_phi007',native_genesis/'experiments/phi_genesis_007.py') if native_genesis else None
    correct=dict(memory=0,cold_enumeration=0,simple_inverse=0)
    totals=dict(predictions_per_method=54,distinct_heldout_pairs=18,relations=9,repeats=3,
        memory_train_audit_acquisitions=45,cold_train_audit_acquisitions=135,
        simple_train_audit_acquisitions=135,initial_unique_evaluation_answers=18,
        memory_observation_rows_loaded=0,memory_sql_statements=0,memory_governance_checks=0,
        memory_hypothesis_row_checks_upper_bound=0,cold_hypothesis_row_checks_upper_bound=0,
        simple_modular_inversions=0,negative_transfer_abstentions=0,naive_negative_transfer_wrong=0,
        native_phi007_agreements=0,native_phi007_validation_observations=0,
        negative_control_hypothesis_row_checks_upper_bound=9*930*3)
    timings=dict(memory_ns=0,cold_ns=0,simple_ns=0,memory_setup_ns=0,native_oracle_ns=0)
    owner=LocalIdentity('fixture:benchmark-operator',secrets.token_bytes(32))
    actor=LocalIdentity('fixture:benchmark-learner',secrets.token_bytes(32))
    context=Context('demo','benchmark','research',('research',))
    for seed in range(9):
        a,b=seed*3+1,(seed*7+4)%31
        rows=[];nodes=[]
        path=out/f'memory-{seed}.sqlite3';guard=out/f'guard-{seed}.sqlite3'
        setup_tick=time.perf_counter_ns()
        with LivingStore.create(path,guard,owner) as store:
            store.register_identity(actor);policy=store.set_policy(1)
            for x,split in enumerate(('train','train','train','audit','audit','test','test')):
                gid='fixture:o'+str(x);y=(a*x+b)%31
                store.add_gene(gid,f'Inert observation {seed} {x}',_metadata(gid),_token(f'{seed}:{x}'))
                observe(store,gid,split,x,y)
                store.grant(gid,actor,context,'learn',now=100,expires_at=200)
                rows.append(dict(node_id=gid,split=split,x=x,y=y))
                nodes.append(dict(node_id=gid,kind='memory',depends_on=[]))
            inventory=dict(schema=RETENTION_SCHEMA,synthetic=True,fixture_id='fixture:benchmark',
                nodes=nodes,coverage={k:'unknown' for k in KINDS})
            timings['memory_setup_ns']+=time.perf_counter_ns()-setup_tick
            for repeat in range(3):
                statements=[]
                store.db.set_trace_callback(lambda sql:statements.append(None))
                tick=time.perf_counter_ns();result=learn(store,actor,context,now=150,expected_policy=policy)
                timings['memory_ns']+=time.perf_counter_ns()-tick
                store.db.set_trace_callback(None)
                totals['memory_sql_statements']+=len(statements)
                correct['memory']+=result['test_matches']
                totals['memory_observation_rows_loaded']+=len(rows)
                totals['memory_governance_checks']+=result['governance_checks']
                totals['memory_hypothesis_row_checks_upper_bound']+=result['hypothesis_row_checks_upper_bound']
                tick=time.perf_counter_ns();cold=experiment(inventory,rows)
                timings['cold_ns']+=time.perf_counter_ns()-tick
                correct['cold_enumeration']+=cold['test_matches']
                totals['cold_hypothesis_row_checks_upper_bound']+=930*3
                tick=time.perf_counter_ns()
                slope=((rows[1]['y']-rows[0]['y'])*pow(rows[1]['x']-rows[0]['x'],-1,31))%31
                rule=(slope,(rows[0]['y']-slope*rows[0]['x'])%31)
                assert all((rule[0]*r['x']+rule[1])%31==r['y'] for r in rows if r['split']!='test')
                correct['simple_inverse']+=sum((rule[0]*r['x']+rule[1])%31==r['y'] for r in rows if r['split']=='test')
                timings['simple_ns']+=time.perf_counter_ns()-tick;totals['simple_modular_inversions']+=1
                if native:
                    tick=time.perf_counter_ns()
                    inferred=native.infer([(r['x'],r['y']) for r in rows if r['split']=='train'])
                    assert inferred==rule;totals['native_phi007_agreements']+=1
                    totals['native_phi007_validation_observations']+=3
                    timings['native_oracle_ns']+=time.perf_counter_ns()-tick
            # Constructed concept drift: keep old training, shift audited truth.
            drift=[dict(r,y=(r['y']+1)%31) if r['split']=='audit' else dict(r) for r in rows]
            totals['negative_transfer_abstentions']+=experiment(inventory,drift)['rule'] is None
            totals['naive_negative_transfer_wrong']+=sum(
                (a*r['x']+b)%31 != (r['y']+1)%31 for r in rows if r['split']=='test')
    totals['persistent_fixture_bytes']=sum(p.stat().st_size for p in out.glob('*.sqlite3'))
    result=dict(schema='genomememory-learning-benchmark/v1',synthetic=True,authority='NONE',
        correct=correct,counts=totals,observed_wall_time_ns=timings,
        audit_answer_comparisons=dict(memory=108,cold=54,simple=54),
        heldout_scoring_comparisons=dict(memory=108,cold=54,simple=54),
        simple_training_consistency_checks=81,
        source_acquisition_unit='One synthetic teacher response under a cold-acquisition or reuse budget; not measured external acquisition time.',
        setup_cost='Each memory method acquires five train/audit observations per relation; included above.',
        scope='Authored finite affine family; repeated predictions are not independent replications.',
        limitations=['No real-world dataset or general intelligence claim.',
            'Both complete validation and admitted fitting costs are charged for memory.',
            'Hypothesis row counts are upper bounds, not hardware instruction counts.',
            'Setup and native-oracle wall time are reported separately from prediction-method wall time.',
            'Persistent bytes include SQLite/guard overhead; baseline source storage is not measured.',
            'Source-acquisition savings reflect repeated-context reuse; simple inverse is computationally much cheaper.'])
    _write(out/'report.json',result)
    return result


def run(out, *, memoria_source=None, sml_packets=None, xi_source=None, genesis_source=None, phios_source=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    exports,source_token=native_exports(out,memoria_source,sml_packets)
    owner=LocalIdentity('fixture:operator',secrets.token_bytes(32))
    sender=LocalIdentity('fixture:sender',secrets.token_bytes(32))
    receiver=LocalIdentity('fixture:receiver',secrets.token_bytes(32))
    context=Context('demo','living-demo','research',('research',))
    path,guard=out/'memory.sqlite3',out/'guard.sqlite3'
    checks=dict.fromkeys(('source_creation','native_export','representation','integrity','consent',
                         'packet_review','learning','revocation','restart'),False)
    with LivingStore.create(path,guard,owner) as store:
        store.register_identity(sender);store.register_identity(receiver);policy=store.set_policy(1)
        gid='fixture:source'
        # Explicitly invented meaning and explicit local consent. Native staging
        # remains HELD; no importance score or unknown policy is promoted.
        store.add_gene(gid,'Explicitly authored synthetic source memory.',_metadata(gid),source_token or _token('source'))
        checks['source_creation']=store.engine.verify()['ok']
        checks['native_export']=exports['memoria']['executed']
        for x,split in enumerate(('train','train','train','audit','audit','test','test')):
            oid='fixture:o'+str(x)
            store.add_gene(oid,'Synthetic affine observation '+str(x),_metadata(oid),_token('o'+str(x)),
                           parents=[gid] if x in (0,1) else [])
            observe(store,oid,split,x,(7*x+4)%31)
            store.grant(oid,sender,context,'learn',now=100,expires_at=200)
        all_ids=[gid]+['fixture:o'+str(x) for x in range(7)]
        store.add_chromosome(MemoryChromosome('root','demo',None,tuple(all_ids[:4])))
        store.add_chromosome(MemoryChromosome('child','demo','root',tuple(all_ids[3:])))
        flat=geometry.snapshot(store,[dict(pocket_id='pocket:root',project='demo',parent_id=None,chromosome_ids=['root']),
            dict(pocket_id='pocket:child',project='demo',parent_id='pocket:root',chromosome_ids=['child'])])
        checks['representation']=geometry.flatten(geometry.nest(flat))==flat
        _write(out/'geometry.json',flat)
        encoded=canonical(flat);checks['integrity']=True
        node=subprocess.run(['node',str(Path(__file__).resolve().parents[2]/'scripts/living_conformance.mjs'),
                             str(out/'geometry.json')],capture_output=True,text=True,check=True)
        node_result=json.loads(node.stdout)
        assert node_result['canonical'].encode()==encoded
        _write(out/'node-conformance.json',dict(checks=node_result['checks'],sha256=node_result['sha256']))
        if xi_source:
            capsule=_load('living_native_xpo_capsule',xi_source/'src/capsule.py')
            # XPO-002 carries a bounded reference commitment, not a large arbitrary catalog.
            value=dict(namespace='genomememory.fixture',operation='integrity-review',
                       atoms=[hashlib.sha256(encoded).hexdigest(),flat['lattice_id'],flat['namespace']])
            wire=capsule.encode(value);assert capsule.decode(wire)==value
            js="import {pathToFileURL} from 'node:url';const m=await import(pathToFileURL(process.argv[1]));let s='';for await(const c of process.stdin)s+=c;const p=Buffer.from(s,'hex');console.log(JSON.stringify({value:m.decode(p),hex:m.encode(m.decode(p)).toString('hex')}));"
            native_node=subprocess.run(['node','--input-type=module','-e',js,str(xi_source/'src/capsule.mjs')],
                input=wire.hex(),capture_output=True,text=True,check=True)
            returned=json.loads(native_node.stdout);assert returned['value']==value and returned['hex']==wire.hex()
            _write(out/'xpo-native.json',dict(executed=True,bytes=len(wire),python_node_agree=True,
                python_source=_source_receipt(xi_source/'src/capsule.py'),node_source=_source_receipt(xi_source/'src/capsule.mjs')))
        held=store.evaluate([gid],sender,context,'express',now=150,expected_policy=policy)
        store.grant(gid,sender,context,'express',now=100,expires_at=200)
        expressed=store.evaluate([gid],sender,context,'express',now=150,expected_policy=policy)
        checks['consent']=not held.admitted_ids and expressed.admitted_ids==(gid,)
        transfer_context=replace(context,destination=receiver.principal_id)
        store.grant(gid,sender,transfer_context,'transfer',now=100,expires_at=200)
        packet=pack(store,[gid],sender,receiver,transfer_context,now=150,expires_at=190,expected_policy=policy)
        receipt=admit(store,packet,sender,receiver,now=151)
        checks['packet_review']=verify_receipt(receipt,receiver) and receipt==admit(store,packet,sender,receiver,now=152)
        learned=learn(store,sender,context,now=150,expected_policy=policy)
        checks['learning']=learned['rule']==[7,4] and learned['test_matches']==2
        affected=store.repair(gid,'revoke').affected_ids
        after=learn(store,sender,context,now=150,expected_policy=policy)
        denied=False
        try:admit(store,packet,sender,receiver,now=153)
        except PermissionError:denied=True
        checks['revocation']=denied and set(affected)=={gid,'fixture:o0','fixture:o1'} and after['rule'] is None
        before=store.reconstruct()
        _write(out/'loop-results.json',dict(learning_rule=learned['rule'],heldout_correct=learned['test_matches'],
            heldout_count=learned['test_count'],after_withdrawal_status=after['status'],
            after_withdrawal_rule=after['rule'],affected_count=len(affected),packet_held_after_withdrawal=denied,
            physical_erasure_verified=False,unknown_external_obligations=store.db.execute('SELECT count(*) FROM lm_obligations').fetchone()[0]))
    with LivingStore.open(path,guard,owner) as restored:
        checks['restart']=restored.reconstruct()==before
    # A distinct process verifies reconstructed state. Key travels only via stdin,
    # never in argv, a log, an environment variable or a committed artifact.
    code="from phimemory9.living_store import LivingStore\nfrom phimemory9.living_contract import LocalIdentity\nimport sys,json\nk=json.load(sys.stdin)\nwith LivingStore.open(sys.argv[1],sys.argv[2],LocalIdentity('fixture:operator',bytes.fromhex(k['key']))) as s:\n assert s._gene('fixture:source')['state']=='held'\n assert s.engine.verify()['ok']\nprint('cold-restart-ok')"
    cold=subprocess.run([sys.executable,'-c',code,str(path),str(guard)],input=json.dumps({'key':owner.key.hex()}),
                        capture_output=True,text=True,check=True)
    checks['restart']=checks['restart'] and cold.stdout.strip()=='cold-restart-ok'
    result_benchmark=benchmark(out/'benchmark',genesis_source)
    details=dict(checks=checks,exports=exports,benchmark=result_benchmark,
                 native_xpo=bool(xi_source),native_phi007=bool(genesis_source),native_sml=bool(sml_packets))
    _write(out/'evidence.json',details)
    report=dict(schema='genomememory-living-demo/v1',synthetic=True,authority='NONE',
        experimental_pass=all(checks.values()),live_ready=False,checks=checks,blockers=BLOCKERS,
        evidence_sha256=hashlib.sha256((out/'evidence.json').read_bytes()).hexdigest())
    _write(out/'advisory.json',report)
    if phios_source:
        native_phios=_load('living_native_phios_advisory',phios_source/'phios/genomememory_advisory.py')
        advisory=native_phios.review(report)
        assert advisory['status']=='HELD' and advisory['evidence_verified'] is False
        _write(out/'phios-advisory.json',advisory)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    for name in ('memoria-source','sml-packets','xi-source','genesis-source','phios-source'):
        parser.add_argument('--'+name,type=Path)
    parser.add_argument('--require-native',action='store_true')
    args=parser.parse_args()
    if args.require_native and not all((args.memoria_source,args.xi_source,args.genesis_source,args.phios_source)):
        parser.error('--require-native requires the four public native source paths; private SML is optional')
    result=run(args.output,memoria_source=args.memoria_source,sml_packets=args.sml_packets,
               xi_source=args.xi_source,genesis_source=args.genesis_source,phios_source=args.phios_source)
    print(json.dumps(result,sort_keys=True,indent=2))
    return 1 if args.require_native and not result['experimental_pass'] else 0


if __name__=='__main__': raise SystemExit(main())
