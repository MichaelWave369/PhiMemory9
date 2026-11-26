"""Persistent governed observations; recompute rules after every policy check.

No model weights or executable payloads. No learned-rule cache can outlive its
source consent. Held-out answers score only; fitting uses training exclusively.
"""
from .genomememory_relational import experiment
from .genomememory_retention import SCHEMA, KINDS


def observe(store, gid, split, x, y):
    if split not in {'train','audit','test'} or any(type(v) is not int or not 0 <= v < 31 for v in (x,y)):
        raise ValueError('invalid finite observation')
    with store.engine.transaction():
        if store._gene(gid)['state'] != 'active' or store.block_action(gid):
            raise PermissionError('held observation source')
        store.db.execute('INSERT INTO lm_observations VALUES (?,?,?,?)', (gid,split,x,y))


def learn(store, identity, context, *, now, expected_policy):
    rows = [dict(node_id=r['gene_id'],split=r['split'],x=r['x'],y=r['y'])
            for r in store.db.execute('SELECT * FROM lm_observations ORDER BY gene_id')]
    if not rows:
        return dict(status='NO_GOVERNED_OBSERVATIONS',rule=None,test_matches=None,test_count=0,
                    excluded_count=0,authority='NONE')
    if len(rows) > 9: raise ValueError('bounded learning fixture supports at most nine observations')
    nodes = []
    for row in store.db.execute('SELECT gene_id FROM lm_genes ORDER BY gene_id'):
        parents = [r[0] for r in store.db.execute('SELECT parent_id FROM lm_lineage WHERE child_id=? ORDER BY parent_id', (row[0],))]
        nodes.append(dict(node_id=row[0],kind='descendant' if parents else 'memory',depends_on=parents))
    inventory = dict(schema=SCHEMA,synthetic=True,fixture_id='fixture:living-learning',nodes=nodes,
                     coverage={k:'unknown' for k in KINDS})
    # Full original split/ancestry validation precedes governance filtering.
    experiment(inventory,rows)
    event = store.evaluate([r['node_id'] for r in rows],identity,context,'learn',
                           now=now,expected_policy=expected_policy)
    admitted = [r for r in rows if r['node_id'] in event.admitted_ids]
    if not admitted:
        return dict(status='NO_GOVERNED_OBSERVATIONS',rule=None,test_matches=None,test_count=0,
                    excluded_count=len(rows),event_id=event.event_id,authority='NONE')
    result = experiment(inventory,admitted)
    return dict(result,excluded_count=len(rows)-len(admitted),event_id=event.event_id,
                acquisition_count=len(rows),governance_checks=len(rows),
                # Both validation and admitted fitting run the enumerator.
                # all() may short-circuit, so this is an explicit upper bound.
                hypothesis_row_checks_upper_bound=930*(sum(r['split']=='train' for r in rows)
                                                      +sum(r['split']=='train' for r in admitted)),
                note='Separate same-author checks; no externally verified evidence or production authority.')
