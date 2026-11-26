"""Living Memory v1: bounded, printable-ASCII, integer-only fixture contracts.

Identity, representation, local storage and authority are separate objects.
Biological names below describe software only.
"""
from dataclasses import dataclass, field
import hashlib
import json

from .genomememory_preview import _label

SCHEMA = 'genomememory-living/v1'
MAX_WIRE = 16384


def canonical(value):
    """Canonical bytes for this restricted dialect, NOT arbitrary JSON/JCS."""
    count = 0

    def validate(v, depth=0):
        nonlocal count
        count += 1
        if count > 4096 or depth > 16:
            raise ValueError('canonical resource bound')
        if v is None or type(v) is bool:
            return
        if type(v) is int and abs(v) <= 2**53-1:
            return
        if type(v) is str and len(v) <= 2048 and all(' ' <= c <= '~' for c in v):
            return
        if type(v) is list and len(v) <= 256:
            for item in v:
                validate(item, depth+1)
            return
        if type(v) is dict and len(v) <= 64:
            for k, item in v.items():
                if type(k) is not str:
                    raise ValueError('string keys required')
                validate(k, depth+1)
                validate(item, depth+1)
            return
        raise ValueError('unsupported canonical type, number or text')

    validate(value)
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True, allow_nan=False).encode('ascii')
    if len(raw) > MAX_WIRE:
        raise ValueError('canonical byte bound')
    return raw


def strict_loads(raw):
    if type(raw) not in (str, bytes) or len(raw) > MAX_WIRE:
        raise ValueError('invalid wire input')

    def unique(pairs):
        out = {}
        for key, val in pairs:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = val
        return out

    try:
        value = json.loads(raw, object_pairs_hook=unique)
        expected = canonical(value)
        wire = raw.encode('ascii') if type(raw) is str else raw
        if wire != expected:
            raise ValueError('wire must use the canonical spelling')
        return value
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid wire input') from exc


def commitment(domain, value):
    return hashlib.sha256(_label(domain).encode('ascii')+b'\0'+canonical(value)).hexdigest()


@dataclass(frozen=True)
class LocalIdentity:
    principal_id: str
    key: bytes = field(repr=False)

    def __post_init__(self):
        fixture_id(self.principal_id)
        if type(self.key) is not bytes or len(self.key) != 32:
            raise ValueError('32-byte fixture key required')


def fixture_id(value):
    value = _label(value)
    if not value.startswith('fixture:') or value == 'fixture:':
        raise ValueError('fixture identity required')
    return value


@dataclass(frozen=True)
class MemoryToken:
    token_id: str
    source_system: str
    source_instance: str
    native_id: str
    source_revision: str


@dataclass(frozen=True)
class MemoryGene:
    gene_id: str
    memory_id: str
    token_id: str
    revision: int
    state: str


@dataclass(frozen=True)
class MemoryChromosome:
    chromosome_id: str
    project: str
    parent_id: str | None
    gene_ids: tuple[str, ...]


@dataclass(frozen=True)
class EpigeneticTag:
    activate: tuple[str, ...]
    suppress: tuple[str, ...]


@dataclass(frozen=True)
class Context:
    project: str
    app: str
    purpose: str
    tags: tuple[str, ...]
    destination: str | None = None


@dataclass(frozen=True)
class ConsentRecord:
    consent_id: str
    gene_id: str
    principal_id: str
    operation: str
    policy_sha256: str
    expires_at: int


@dataclass(frozen=True)
class ExpressionEvent:
    event_id: str
    admitted_ids: tuple[str, ...]
    held: tuple[tuple[str, str], ...]
    policy_sha256: str
    operation: str


@dataclass(frozen=True)
class RepairEvent:
    event_id: str
    action: str
    affected_ids: tuple[str, ...]


@dataclass(frozen=True)
class LineageRecord:
    child_id: str
    parent_id: str


@dataclass(frozen=True)
class RetentionObligation:
    obligation_id: str
    kind: str
    status: str
