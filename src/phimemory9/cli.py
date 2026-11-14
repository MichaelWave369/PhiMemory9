"""Minimal CLI for the nine-operation prototype."""
import argparse
import json

from .core import MemoryEngine


def main() -> None:
    parser = argparse.ArgumentParser(prog="phi-memory9")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run an auditable nested loop")
    demo.add_argument("--db", default=":memory:")
    verify = commands.add_parser("verify", help="Check storage and lineage integrity")
    verify.add_argument("--db", required=True)
    args = parser.parse_args()

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
            print(json.dumps({
                "root_blob": root, "root_memory": memory,
                "gear": gear,
                "child_lineage": [x["id"] for x in payload["lineage"]],
                "verified": engine.verify(),
            }, indent=2))
        else:
            report = engine.verify()
            print(json.dumps(report, indent=2))
            if not report["ok"]:
                raise SystemExit(1)


if __name__ == "__main__":
    main()
