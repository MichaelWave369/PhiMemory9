"""CLI for the deterministic ΦMemory9 research prototype."""
import argparse
import json

from .core import MemoryEngine
from .evidence import EvidenceLedger
from .retrieval import benchmark_fixture


def main() -> None:
    parser = argparse.ArgumentParser(prog="phi-memory9")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run an auditable nested loop")
    demo.add_argument("--db", default=":memory:")
    verify = commands.add_parser("verify", help="Check base storage and lineage")
    verify.add_argument("--db", required=True)
    edemo = commands.add_parser(
        "evidence-demo", help="Run an operator-declared synthetic contradiction"
    )
    edemo.add_argument("--db", default=":memory:")
    ev = commands.add_parser(
        "verify-evidence", help="Audit both base memory and R0.2 evidence"
    )
    ev.add_argument("--db", required=True)
    commands.add_parser(
        "benchmark", help="Compare literal and lineage retrieval on synthetic data"
    )
    args = parser.parse_args()

    if args.command == "benchmark":
        print(json.dumps(benchmark_fixture(), indent=2))
        return

    with MemoryEngine(args.db) as engine:
        if args.command == "demo":
            root = engine.create_blob("Observation")
            memory = engine.enter(
                root, "A system gains a new fact.",
                source_ref="example:synthetic",
            )
            gear = engine.loop(memory, route="inward")
            child = gear["child_memory_id"]
            payload = engine.liberation(child)
            report = {
                "root_blob": root, "root_memory": memory,
                "gear": gear,
                "child_lineage": [x["id"] for x in payload["lineage"]],
                "verified": engine.verify(),
            }
        elif args.command == "evidence-demo":
            root = engine.create_blob("Synthetic evidence")
            memory = engine.enter(root, "Synthetic reading recorded", "fixture:r0.2")
            ledger = EvidenceLedger(engine)
            source = ledger.source(
                "Fictional lab log", "fixture:r02", kind="synthetic",
            )
            a = ledger.claim(memory, "Sensor is operational")
            b = ledger.claim(memory, "Sensor is not operational")
            ledger.attach(a, source, "context", excerpt="Reading was recorded")
            ledger.contradiction(a, b, "Opposing interpretations")
            report = {"claim_a": ledger.report(a), "claim_b": ledger.report(b),
                      "audit": ledger.audit()}
        elif args.command == "verify-evidence":
            report = EvidenceLedger(engine).audit()
        else:
            report = engine.verify()
        print(json.dumps(report, indent=2))
        if args.command in ("verify", "verify-evidence") and not report["ok"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
