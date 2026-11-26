"""R0.9 fixed synthetic integration harness. No live inputs or runtime effects."""
import argparse
import json

from .genomememory_preview import preview
from .genomememory_chromosomes import chromosome_preview
from .genomememory_integrity import receipt, _digest
from . import genomememory_memoria as memoria
from . import genomememory_sml as sml
from . import phageledger_packets as packets
from . import genomememory_retention as retention
from .genomememory_relational import experiment

DOMAIN = "genomememory/integration/r0.9"
BLOCKERS = (
    "native_source_exports_and_authorized_read_access",
    "authenticated_endpoint_and_consent_lifecycle",
    "enforced_revocation_and_verified_storage_erasure",
    "durable_replay_and_restore_guards",
    "cross_language_contract_conformance",
    "independent_evaluation_and_security_review",
    "native_phios_and_phigenesis_runtime_integration",
)
SCENARIOS = ("baseline", "contradiction", "withdrawal", "expired",
             "wrong_destination", "tampered", "insufficient")


def _fixtures():
    stamp = "2026-06-20T12:00:00+00:00"
    m = dict(schema=memoria.SNAPSHOT_SCHEMA, synthetic=True,
             source_revision=memoria.SOURCE_REVISION, fixture_id="fixture:memoria",
             rows=[dict(id=1, app_name="demo", agent_id="fixture:author",
                        timestamp=stamp, tags=["research"], importance_score=1,
                        encrypted=0)])
    p = dict(memory_id="fixture:sml-record", author_agent_id="fixture:author",
             timestamp=stamp, state="active", collab_state="shared_verified",
             fork_group_id=None)
    p.update({k: 1 for k in sml.SCORES})
    p.update({k: [] for k in sml.LISTS})
    s = dict(schema=sml.SCHEMA, synthetic=True, source_revision=sml.REVISION,
             fixture_id="fixture:sml", packets=[p])

    # Separate invented evidence lane: no source staging row becomes a gene.
    nodes = [dict(node_id="fixture:source", kind="memory", depends_on=[])]
    observations, genes = [], []
    for x, split in enumerate(("train", "train", "train", "audit", "audit", "test", "test")):
        nid = f"fixture:o{x}"
        parents = ["fixture:source"] if x in (2, 4, 6) else []
        nodes.append(dict(node_id=nid, kind="descendant" if parents else "memory",
                          depends_on=parents))
        observations.append(dict(node_id=nid, split=split, x=x, y=(7*x+4)%31))
        genes.append(dict(gene_id=nid, project="demo", privacy="public",
                          consent="safe_to_use", repair="clean", confidence="high",
                          claim="fact", source_refs=["fixture:invented-evidence"],
                          activate=["research"], suppress=[]))
    nodes.append(dict(node_id="fixture:backup", kind="backup",
                      depends_on=["fixture:o2"]))
    inventory = dict(schema=retention.SCHEMA, synthetic=True,
                     fixture_id="fixture:integration",
                     coverage={k: "declared_complete" for k in retention.KINDS},
                     nodes=nodes)
    groups = [dict(chromosome_id="root", project="demo", parent_id=None,
                   gene_ids=[g["gene_id"] for g in genes[:3]]),
              dict(chromosome_id="child", project="demo", parent_id="root",
                   gene_ids=[g["gene_id"] for g in genes[2:]])]
    return m, s, genes, groups, inventory, observations


def scenario(name):
    if name not in SCENARIOS:
        raise ValueError("unknown fixed scenario")
    m, s, genes, groups, inventory, rows = _fixtures()
    # Review and stage independently, never importing source-system authority.
    m_stage = memoria.stage_snapshot(m, "demo",
                                     memoria.review_snapshot(m, "demo")["snapshot_sha256"])
    s_stage = sml.stage_snapshot(s, "fixture:sml",
                                 sml.review_snapshot(s, "fixture:sml")["snapshot_sha256"])
    if name in ("contradiction", "withdrawal"):
        rows[2]["y"] = (rows[2]["y"]+1) % 31
    target = "fixture:source" if name == "withdrawal" else "fixture:o0" if name == "insufficient" else None
    if name == "insufficient":
        # Only x=1 survives training; x=2 is absent from the experiment.
        rows = [r for r in rows if r["node_id"] != "fixture:o2"]
        genes = [g for g in genes if g["gene_id"] != "fixture:o2"]
        for group in groups:
            group["gene_ids"] = [gid for gid in group["gene_ids"] if gid != "fixture:o2"]
    hold = retention.plan(inventory, target, "revoke") if target else None
    blocked = {o["node_id"] for o in hold["obligations"]} if hold else set()
    # Explicit synthetic preview overlay. This does not enforce real revocation.
    for g in genes:
        if g["gene_id"] in blocked:
            g["repair"] = "needs_review"
    flat = preview(genes, "demo", ["research"], limit=9)
    nested = chromosome_preview(genes, groups, "root", "demo", ["research"], limit=9)
    integrity = receipt(genes, groups, "root", "demo", ["research"], limit=9)
    learned = experiment(inventory, rows, hold_target=target)
    payload = _digest(DOMAIN+"/payload-reference", {
        "memoria": m_stage["snapshot_sha256"], "sml": s_stage["snapshot_sha256"],
        "catalog": integrity["receipt_sha256"], "learning": learned["report_sha256"]})
    policy = _digest(DOMAIN+"/policy-reference", {
        "authority": "NONE", "hold": hold["plan_sha256"] if hold else None})
    envelope = dict(schema=packets.SCHEMA, synthetic=True,
                    packet_id="fixture:integration-packet", source="fixture:phimemory9",
                    destination="fixture:phios-review", purpose="integrity_review",
                    not_before=100, expires_at=200, payload_kind="synthetic_metadata_digest",
                    payload_sha256=payload, policy_sha256=policy, authority="NONE")
    sealed = packets.seal(envelope)["envelope_sha256"]
    if name == "tampered":
        envelope["policy_sha256"] = "0"*64
    inspection = packets.inspect(
        envelope, sealed, expected_source="fixture:phimemory9",
        expected_destination="fixture:other" if name == "wrong_destination" else "fixture:phios-review",
        expected_purpose="integrity_review", expected_payload_sha256=payload,
        expected_policy_sha256=policy, now=200 if name == "expired" else 150)
    status = {"contradiction": "TRAIN_CONTRADICTION", "insufficient": "UNDERDETERMINED"}.get(name, "AUDIT_MATCHED")
    expected_excluded = {"withdrawal": ["fixture:o2", "fixture:o4", "fixture:o6"],
                         "insufficient": ["fixture:o0"]}.get(name, [])
    expected_compatible = name not in ("expired", "wrong_destination", "tampered")
    staged = m_stage["candidates"] + s_stage["candidates"]
    preview_ids = nested["eligible_ids"]
    checks = {
        "source_rows_held": len(staged) == 2 and all(
            c["status"] == "HELD" and c["eligible"] is False
            and len(c["policy"]) == 9 and all(v is None for v in c["policy"].values())
            for c in staged),
        "flat_nested_agree": flat["eligible_ids"] == preview_ids
                            and nested["duplicate_memberships"] == (0 if name == "insufficient" else 1),
        "hold_excluded_from_preview": not blocked.intersection(preview_ids),
        "learning_expected": learned["status"] == status
                             and learned["rule"] == ([7, 4] if status == "AUDIT_MATCHED" else None),
        "heldout_expected": learned["test_matches"] == (learned["test_count"] if status == "AUDIT_MATCHED" else None),
        "withdrawal_propagates": learned["excluded_ids"] == expected_excluded
                                 and learned["hold_plan_sha256"] == (hold["plan_sha256"] if hold else None)
                                 and (hold is None or not hold["applied"] and not hold["erasure_verified"]),
        "packet_expected": inspection["compatible"] is expected_compatible,
        "authority_never_granted": all(r["authority"] == "NONE" for r in
            (m_stage, s_stage, flat, nested, integrity, learned, inspection))
            and not learned["certified"] and not learned["eligible"]
            and not inspection["eligible"] and inspection["status"] == "HELD",
    }
    body = dict(name=name, checks=checks, preview_count=len(preview_ids),
                held_source_count=len(staged), learning_status=learned["status"],
                excluded_count=len(learned["excluded_ids"]), test_matches=learned["test_matches"],
                test_count=learned["test_count"], packet_compatible=inspection["compatible"],
                packet_checks=inspection["checks"], authority="NONE",
                receipts=dict(integrity=integrity["receipt_sha256"],
                              learning=learned["report_sha256"],
                              packet=inspection["receipt_sha256"],
                              hold=hold["plan_sha256"] if hold else None))
    return {**body, "scenario_sha256": _digest(DOMAIN+"/scenario", body)}


def report():
    cases = [scenario(name) for name in SCENARIOS]
    body = dict(schema="genomememory-integration/r0.9", synthetic=True,
                authority="NONE", experimental_pass=all(all(c["checks"].values()) for c in cases),
                live_ready=False, readiness_blockers=list(BLOCKERS), scenarios=cases)
    return {**body, "report_sha256": _digest(DOMAIN+"/report", body)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("report", "gate"))
    args = parser.parse_args()
    result = report()
    print(json.dumps(result, sort_keys=True, indent=2))
    if not result["experimental_pass"]:
        return 1
    return 3 if args.mode == "gate" else 0


if __name__ == "__main__":
    raise SystemExit(main())
