"""Reversible nested selectors over shared identities, without geometric claims."""
import copy
import json

from .genomememory_chromosomes import chromosome_preview, MAX_DEPTH
from .genomememory_preview import _label, _labels
from .living_contract import canonical, fixture_id

SCHEMA = 'genomememory-geometry/v1'


def validate(snapshot):
    canonical(snapshot)
    if type(snapshot) is not dict or set(snapshot) != {
        'schema','lattice_id','namespace','project','genes','chromosomes','pockets','sources'}:
        raise ValueError('invalid lattice fields')
    if snapshot['schema'] != SCHEMA: raise ValueError('unknown lattice schema')
    fixture_id(snapshot['lattice_id']); fixture_id(snapshot['namespace'])
    project = _label(snapshot['project'])
    genes, groups = snapshot['genes'], snapshot['chromosomes']
    if not groups: raise ValueError('chromosomes required')
    chromosome_preview(genes,groups,groups[0]['chromosome_id'],project,[],limit=0)
    if any(g['project'] != project for g in genes+groups): raise ValueError('cross-project lattice')
    gids = {g['gene_id'] for g in genes}
    sources = snapshot['sources']
    if type(sources) is not list or len(sources) != len(gids): raise ValueError('source identities required')
    seen = set()
    for source in sources:
        if type(source) is not dict or set(source) != {'gene_id','native_memory_id','token'}:
            raise ValueError('invalid source binding')
        gid = source['gene_id']
        if gid not in gids or gid in seen: raise ValueError('duplicate or unknown source identity')
        seen.add(gid); _label(source['native_memory_id'])
        if type(source['token']) is not dict or set(source['token']) != {
            'token_id','source_system','source_instance','native_id','source_revision'}:
            raise ValueError('unknown native token shape')
        for value in source['token'].values(): _label(value)
        fixture_id(source['token']['token_id']); fixture_id(source['token']['source_instance'])
    pockets = snapshot['pockets']
    if type(pockets) is not list or not 1 <= len(pockets) <= 64: raise ValueError('bounded pockets required')
    known = {c['chromosome_id'] for c in groups}
    by_id, linked = {}, set()
    for pocket in pockets:
        if type(pocket) is not dict or set(pocket) != {'pocket_id','parent_id','project','chromosome_ids'}:
            raise ValueError('invalid pocket fields')
        pid = _label(pocket['pocket_id'])
        if pid in by_id or pocket['project'] != project: raise ValueError('duplicate pocket or scope mismatch')
        if pocket['parent_id'] is not None: _label(pocket['parent_id'])
        members = _labels(pocket['chromosome_ids'])
        if not members <= known: raise ValueError('unknown chromosome reference')
        linked.update(members); by_id[pid] = pocket
    if linked != known: raise ValueError('unaddressed chromosome')
    for pid in by_id:
        path, node = set(), pid
        while node is not None:
            if node not in by_id or node in path: raise ValueError('unknown parent or pocket cycle')
            path.add(node)
            if len(path) > MAX_DEPTH: raise ValueError('pocket depth exceeded')
            node = by_id[node]['parent_id']
    result = copy.deepcopy(snapshot)
    for gene in result['genes']:
        for key in ('source_refs','activate','suppress'): gene[key] = sorted(gene[key])
    for c in result['chromosomes']: c['gene_ids'] = sorted(c['gene_ids'])
    for p in result['pockets']: p['chromosome_ids'] = sorted(p['chromosome_ids'])
    for field, key in (('genes','gene_id'),('chromosomes','chromosome_id'),
                       ('sources','gene_id'),('pockets','pocket_id')):
        result[field].sort(key=lambda row:row[key])
    canonical(result)
    return result


def snapshot(store, pockets, *, lattice_id='fixture:lattice', project='demo'):
    genes, groups = store.catalog()
    sources = []
    for gene in genes:
        row = store._gene(gene['gene_id'])
        token = store.db.execute('SELECT source_json FROM lm_tokens WHERE token_id=?', (row['token_id'],)).fetchone()
        sources.append(dict(gene_id=gene['gene_id'],native_memory_id=row['memory_id'],token=json.loads(token[0])))
    return validate(dict(schema=SCHEMA,lattice_id=lattice_id,namespace=store._meta('store_id'),
        project=project,genes=genes,chromosomes=groups,pockets=pockets,sources=sources))


def nest(flat):
    flat = validate(flat)
    pockets = flat.pop('pockets')

    def build(parent):
        return [dict(pocket_id=p['pocket_id'],project=p['project'],chromosome_ids=p['chromosome_ids'],
                     children=build(p['pocket_id'])) for p in pockets if p['parent_id'] == parent]

    return dict(catalog=flat,roots=build(None))


def flatten(nested):
    canonical(nested)
    if type(nested) is not dict or set(nested) != {'catalog','roots'}:
        raise ValueError('invalid nested lattice')
    pockets = []

    def walk(rows, parent, depth=1):
        if type(rows) is not list or len(rows) > 64 or depth > MAX_DEPTH+1:
            raise ValueError('invalid nested pocket bound')
        for row in rows:
            if type(row) is not dict or set(row) != {'pocket_id','project','chromosome_ids','children'}:
                raise ValueError('invalid nested pocket')
            pockets.append(dict(pocket_id=row['pocket_id'],project=row['project'],
                                 chromosome_ids=row['chromosome_ids'],parent_id=parent))
            walk(row['children'],row['pocket_id'],depth+1)
    walk(nested['roots'],None)
    if 'pockets' in nested['catalog']: raise ValueError('ambiguous nested catalog')
    return validate(dict(nested['catalog'],pockets=pockets))
