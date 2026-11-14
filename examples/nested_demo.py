"""Minimal public fixture: source memory -> ninth-gear inward transfer."""
from phimemory9 import MemoryEngine


with MemoryEngine() as engine:
    origin = engine.create_blob("Original observation")
    first = engine.enter(
        origin, "Knowledge begins as an observation.", "fixture:observation-1"
    )
    gear = engine.loop(first, "inward")
    second = gear["child_memory_id"]
    assert second is not None
    print("Nine-stage vocabulary:", ", ".join(__import__("phimemory9").STAGES))
    print("Gear:", gear)
    print("Child ancestry:", engine.lineage(second))
    print("Source remains:", engine.memory(first)["content"])
    print("Integrity:", engine.verify())
