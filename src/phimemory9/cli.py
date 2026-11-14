"""CLI for the deterministic ΦMemory9 research prototype."""
import argparse
import json

from .core import MemoryEngine
from .evidence import EvidenceLedger
from .retrieval import benchmark_fixture
from .governance import (
    apply, export_digest, load_plan, review, save_export,
)
from .local_lab import make_server, seed_lab


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
    seed = commands.add_parser(
        "seed-lab", help="Create a new synthetic SQLite fixture database (never overwrite)"
    )
    seed.add_argument("--db", required=True)
    serve = commands.add_parser(
        "serve", help="Serve compiled React plus read-only SQLite inspector on loopback"
    )
    serve.add_argument("--db", required=True)
    serve.add_argument("--port", type=int, default=8769)
    serve.add_argument("--web-dir", default=None)
    plan_review = commands.add_parser(
        "plan-review", help="Inspect a proposed local mutation and its SHA-256"
    )
    plan_review.add_argument("--db", required=True)
    plan_review.add_argument("--plan", required=True)
    plan_apply = commands.add_parser(
        "apply-plan", help="Apply a reviewed plan by exact SHA-256 approval"
    )
    plan_apply.add_argument("--db", required=True)
    plan_apply.add_argument("--plan", required=True)
    plan_apply.add_argument("--approve-sha256", required=True)
    export_review = commands.add_parser(
        "export-review", help="Review digest needed for local full export"
    )
    export_review.add_argument("--db", required=True)
    export_review.add_argument("--memory", required=True)
    export_memory = commands.add_parser(
        "export-memory", help="Save an explicitly requested local privacy export"
    )
    export_memory.add_argument("--db", required=True)
    export_memory.add_argument("--memory", required=True)
    export_memory.add_argument("--out", required=True)
    export_memory.add_argument("--include-content", action="store_true")
    export_memory.add_argument("--approve-sha256", default=None)
    args = parser.parse_args()

    if args.command == "seed-lab":
        print(json.dumps(seed_lab(args.db), indent=2))
        return

    if args.command == "serve":
        server = make_server(args.db, args.port, args.web_dir)
        print(f"Read-only ΦMemory9 lab: http://127.0.0.1:{server.server_port}/PhiMemory9/")
        print("ACCESS KEY (paste into local browser; never put in URL):")
        print(server.access_token)
        print("Keep this terminal key private; it changes on every server restart.")
        print("LOCAL INSPECTION ONLY · CTRL+C to stop · No write API")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return

    if args.command == "benchmark":
        print(json.dumps(benchmark_fixture(), indent=2))
        return

    with MemoryEngine(args.db) as engine:
        if args.command == "plan-review":
            report = review(engine, load_plan(args.plan))
        elif args.command == "apply-plan":
            report = apply(engine, load_plan(args.plan), args.approve_sha256)
        elif args.command == "export-review":
            report = {
                "schema": "phi-memory9/privacy-export-r0.4",
                "memory_id": args.memory,
                "full_export_sha256": export_digest(engine, args.memory),
                "notice": "Approve exact content-bound digest only if full export is intended.",
            }
        elif args.command == "export-memory":
            report = save_export(
                engine, args.memory, args.out,
                include_content=args.include_content,
                approved_sha256=args.approve_sha256,
            )
        elif args.command == "demo":
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
